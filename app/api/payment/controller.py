import json
import uuid
import logging
from functools import wraps

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction, DatabaseError
from django.core.exceptions import ValidationError as DjangoValidationError

from app.models.users import User
from app.models.delivery import Delivery
from app.models.payment import Payment, PaymentRefund
from app.helpers.enums import PaymentStatus, PaymentMethod
from app.helpers.razorpay_service import razorpay_service
from app.helpers.decorators import handle_validation_error
from app.helpers.validators import (
    PaymentValidator,
    RefundValidator,
    validate_json_body
)
from app.helpers.pagination import PaginationHelper
from app.helpers.redis_service import RedisService
from app.helpers.exceptions import (
    APIError, BadRequestError, NotFoundError, ConflictError, 
    ValidationError, DatabaseError as DBError, ServiceUnavailableError
)


logger = logging.getLogger(__name__)


# =====================================================
# PAYMENT ORDER CREATION
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentOrderController(View):
    """
    Create payment order for delivery
    """

    def post(self, request):
        try:
            # Validate Razorpay service availability
            if not razorpay_service:
                raise ServiceUnavailableError("Payment service is currently unavailable")

            # Parse and validate JSON body
            body = validate_json_body(request)
            validated_data = PaymentValidator.validate_payment_creation(body)

            # Verify user exists
            user = User.objects.filter(id=validated_data["user_id"]).first()
            if not user:
                raise NotFoundError("User not found")

            # Verify delivery exists and belongs to user
            delivery = Delivery.objects.filter(
                id=validated_data["delivery_id"],
                end_user_id=validated_data["user_id"]
            ).first()
            
            if not delivery:
                raise NotFoundError("Delivery not found or does not belong to user")

            # Check if payment already exists for this delivery
            existing_payment = Payment.objects.filter(
                delivery_id=validated_data["delivery_id"],
                status__in=[PaymentStatus.PENDING, PaymentStatus.COMPLETED]
            ).first()
            
            if existing_payment:
                raise ConflictError("Payment already exists for this delivery")

            # Create Razorpay order
            try:
                razorpay_order = razorpay_service.create_order(
                    amount=validated_data["amount"],
                    receipt=f"ORD{delivery.id}{user.id}"
                )
            except Exception as e:
                logger.error(f"Failed to create Razorpay order: {str(e)}")
                raise DBError("Failed to create payment order")

            # Create payment record
            payment = Payment(
                razorpay_order_id=razorpay_order["id"],
                user_id=user.id,
                delivery_id=delivery.id,
                amount=validated_data["amount"],
                status=PaymentStatus.PENDING,
                payment_method=PaymentMethod.RAZORPAY
            )
            payment.save()

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
            if not isinstance(e, APIError):
                logger.error(f"Payment order creation failed: {str(e)}")
                raise DBError("Failed to create payment order") from e
            raise


# =====================================================
# PAYMENT VERIFICATION
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class PaymentVerificationController(View):
    """
    Verify Razorpay payment after successful payment
    """

    def post(self, request):
        try:
            # Validate Razorpay service availability
            if not razorpay_service:
                raise ServiceUnavailableError("Payment service is currently unavailable")

            # Parse and validate JSON body
            body = validate_json_body(request)
            
            # Validate required fields
            required_fields = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]
            for field in required_fields:
                if field not in body:
                    raise BadRequestError(f"Missing required field: {field}")

            razorpay_order_id = body["razorpay_order_id"].strip()
            razorpay_payment_id = body["razorpay_payment_id"].strip()
            razorpay_signature = body["razorpay_signature"].strip()

            # Find payment record
            payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if not payment:
                raise NotFoundError("Payment order not found")

            if payment.status != PaymentStatus.PENDING:
                raise BadRequestError(f"Payment already {payment.status.lower()}")

            # Verify Razorpay signature
            try:
                is_valid = razorpay_service.verify_payment(
                    razorpay_order_id,
                    razorpay_payment_id,
                    razorpay_signature
                )
            except Exception as e:
                logger.error(f"Payment verification error: {str(e)}")
                raise DBError("Payment verification failed")

            if not is_valid:
                payment.status = PaymentStatus.FAILED
                payment.save()
                raise BadRequestError("Invalid payment signature")

            # Update payment with verification details
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = PaymentStatus.COMPLETED
            payment.save()

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
            if not isinstance(e, APIError):
                logger.error(f"Payment verification failed: {str(e)}")
                raise DBError("Payment verification failed") from e
            raise


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
                raise NotFoundError("User not found")
            
            # Get pagination parameters
            page, page_size = PaginationHelper.get_pagination_params(request)
            cache_key = f"payment_history:{user_id}:page_{page}:size_{page_size}"
            
            # Try to get from cache first
            cached_result = RedisService.get_cached_query_result(cache_key)
            if cached_result:
                return JsonResponse({
                    "status": "success",
                    "data": cached_result
                })
            
            # Get payments for user with pagination
            payments = Payment.objects.filter(
                user_id=user_id
            ).order_by('-created_at')
            
            # Convert queryset to list of dicts for pagination
            payment_list = list(payments.values(
                'id', 'order_id', 'amount', 'currency', 'status',
                'payment_method', 'created_at', 'updated_at'
            ))
            
            if not payment_list:
                raise NotFoundError("No payment history found")
                
            result = PaginationHelper.paginate_queryset(payment_list, page, page_size)
            
            response_data = {
                "status": "success",
                "data": {
                    "payments": result['data'],
                    "pagination": result['pagination']
                }
            }
            
            # Cache the result for 5 minutes
            RedisService.cache_query_result(cache_key, response_data['data'], timeout=300)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            if not isinstance(e, APIError):
                logger.error(f"Error in PaymentHistoryController: {str(e)}")
                raise DBError("Failed to retrieve payment history") from e
            raise


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
