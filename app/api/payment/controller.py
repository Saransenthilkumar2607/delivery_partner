import json
import uuid
import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from app.models.users import User
from app.models.delivery import Delivery
from app.models.payment import Payment, PaymentRefund
from app.helpers.enums import PaymentStatus, PaymentMethod
from app.helpers.razorpay_service import razorpay_service
from app.helpers.validators import (
    PaymentValidator,
    RefundValidator,
    handle_validation_error, 
    validate_json_body,
    ValidationException
)
from app.helpers.pagination import PaginationHelper
# Temporarily disable SQLAlchemy to isolate database error
# from app.helpers.database import get_database_session


logger = logging.getLogger(__name__)


# =====================================================
# PAYMENT ORDER CREATION
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentOrderController(View):
    """
    Create payment order for delivery
    """

    @handle_validation_error
    def post(self, request):
        # Validate Razorpay service availability
        if not razorpay_service:
            return JsonResponse({
                "error": "Payment service is currently unavailable"
            }, status=503)

        # Parse and validate JSON body
        body = validate_json_body(request)
        validated_data = PaymentValidator.validate_payment_creation(body)

        try:
            # Verify user exists
            user = User.objects.filter(id=validated_data["user_id"]).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Verify delivery exists and belongs to user
            delivery = Delivery.objects.filter(
                id=validated_data["delivery_id"],
                end_user_id=validated_data["user_id"]
            ).first()
            
            if not delivery:
                return JsonResponse({
                    "error": "Delivery not found or does not belong to user"
                }, status=404)

            # Check if payment already exists for this delivery
            existing_payment = Payment.objects.filter(
                delivery_id=validated_data["delivery_id"],
                status__in=[PaymentStatus.PENDING, PaymentStatus.COMPLETED]
            ).first()
            
            if existing_payment:
                return JsonResponse({
                    "error": "Payment already exists for this delivery"
                }, status=409)

            # Create Razorpay order
            try:
                razorpay_order = razorpay_service.create_order(
                    amount=validated_data["amount"],
                    receipt=f"ORD{delivery.id}{user.id}"
                )
            except Exception as e:
                logger.error(f"Failed to create Razorpay order: {str(e)}")
                return JsonResponse({
                    "error": "Failed to create payment order"
                }, status=500)

            # Create payment record
            payment = Payment(
                razorpay_order_id=razorpay_order["id"],
                user_id=user.id,
                delivery_id=delivery.id,
                amount=validated_data["amount"],
                status=PaymentStatus.PENDING,
                payment_method=PaymentMethod.RAZORPAY
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)

            return JsonResponse({
                "message": "Payment order created successfully",
                "order": {
                    "id": payment.id,
                    "razorpay_order_id": razorpay_order["id"],
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "razorpay_key": razorpay_order.get("notes", {}).get("key", "")
                }
            }, status=201)
        except Exception as e:
            session.rollback()
            logger.error(f"Payment order creation failed: {str(e)}")
            return JsonResponse({
                "error": "Failed to create payment order"
            }, status=500)
        finally:
            session.close()


# =====================================================
# PAYMENT VERIFICATION
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentVerificationController(View):
    """
    Verify Razorpay payment after successful payment
    """

    def post(self, request):
        # Validate Razorpay service availability
        if not razorpay_service:
            return JsonResponse({
                "error": "Payment service is currently unavailable"
            }, status=503)

        # Parse and validate JSON body
        body = validate_json_body(request)
        
        # Validate required fields
        required_fields = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]
        for field in required_fields:
            if field not in body:
                return JsonResponse({
                    "error": f"Missing required field: {field}"
                }, status=400)

        razorpay_order_id = body["razorpay_order_id"].strip()
        razorpay_payment_id = body["razorpay_payment_id"].strip()
        razorpay_signature = body["razorpay_signature"].strip()

        session = get_database_session()
        try:
            # Find payment record
            payment = session.query(Payment).filter(Payment.razorpay_order_id == razorpay_order_id).first()
            if not payment:
                return JsonResponse({
                    "error": "Payment order not found"
                }, status=404)

            if payment.status != PaymentStatus.PENDING:
                return JsonResponse({
                    "error": f"Payment already {payment.status.lower()}",
                    "payment_status": payment.status
                }, status=400)

            # Verify Razorpay signature
            try:
                is_valid = razorpay_service.verify_payment(
                    razorpay_order_id,
                    razorpay_payment_id,
                    razorpay_signature
                )
            except Exception as e:
                logger.error(f"Payment verification error: {str(e)}")
                return JsonResponse({
                    "error": "Payment verification failed"
                }, status=500)

            if not is_valid:
                payment.status = PaymentStatus.FAILED
                session.commit()
                return JsonResponse({
                    "error": "Invalid payment signature"
                }, status=400)

            # Update payment with verification details
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = PaymentStatus.COMPLETED
            session.commit()
            session.refresh(payment)

            return JsonResponse({
                "message": "Payment verified successfully",
                "payment": {
                    "id": payment.id,
                    "razorpay_order_id": payment.razorpay_order_id,
                    "razorpay_payment_id": payment.razorpay_payment_id,
                    "amount": float(payment.amount),
                    "status": payment.status
                }
            })
        except Exception as e:
            session.rollback()
            logger.error(f"Payment verification failed: {str(e)}")
            return JsonResponse({
                "error": "Payment verification failed"
            }, status=500)
        finally:
            session.close()


# =====================================================
# PAYMENT HISTORY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentHistoryController(View):
    """
    Get payment history for a user
    """

    def get(self, request, user_id):
        try:
            # Verify user exists
            user = User.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({
                    "error": "User not found"
                }, status=404)
            
            # Get payments for user
            payments_queryset = Payment.objects.filter(user_id=user_id).order_by('-created_at')
            
            page, page_size = PaginationHelper.get_pagination_params(request)
            paginated_result = PaginationHelper.paginate_queryset(
                payments_queryset.values(
                    'id', 'razorpay_order_id', 'razorpay_payment_id', 
                    'amount', 'currency', 'status', 'payment_method', 'created_at'
                ), page, page_size
            )

            return JsonResponse({
                "user_id": user_id,
                "payments": paginated_result['data'],
                "pagination": paginated_result['pagination']
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# PAYMENT REFUND
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentRefundController(View):
    """
    Process payment refund
    """

    @handle_validation_error
    def post(self, request):
        # Validate Razorpay service availability
        if not razorpay_service:
            return JsonResponse({
                "error": "Payment service is currently unavailable"
            }, status=503)

        # Parse and validate JSON body
        body = validate_json_body(request)
        validated_data = RefundValidator.validate_refund_creation(body)

        session = get_database_session()
        try:
            # Find payment record
            payment = session.query(Payment).filter(Payment.id == validated_data["payment_id"]).first()
            if not payment:
                return JsonResponse({
                    "error": "Payment not found"
                }, status=404)

            if payment.status != PaymentStatus.COMPLETED:
                return JsonResponse({
                    "error": "Only completed payments can be refunded"
                }, status=400)

            # Process Razorpay refund
            try:
                razorpay_refund = razorpay_service.refund_payment(
                    razorpay_payment_id=payment.razorpay_payment_id,
                    amount=validated_data.get("amount"),
                    reason=validated_data.get("reason")
                )
            except Exception as e:
                logger.error(f"Razorpay refund failed: {str(e)}")
                return JsonResponse({
                    "error": "Refund processing failed"
                }, status=500)

            # Create refund record
            refund = PaymentRefund(
                payment_id=payment.id,
                razorpay_refund_id=razorpay_refund.get("id"),
                amount=validated_data.get("amount", payment.amount),
                reason=validated_data.get("reason"),
                status=PaymentStatus.COMPLETED
            )
            session.add(refund)
            session.commit()
            session.refresh(refund)

            return JsonResponse({
                "message": "Refund processed successfully",
                "refund": {
                    "id": refund.id,
                    "payment_id": payment.id,
                    "amount": float(refund.amount),
                    "reason": refund.reason,
                    "razorpay_refund_id": refund.razorpay_refund_id,
                    "status": refund.status
                }
            }, status=201)
        except Exception as e:
            session.rollback()
            logger.error(f"Refund processing failed: {str(e)}")
            return JsonResponse({
                "error": "Refund processing failed"
            }, status=500)
        finally:
            session.close()
