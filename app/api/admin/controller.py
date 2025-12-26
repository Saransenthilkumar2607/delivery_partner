import json
import uuid
import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone

from app.models.users import User
from app.models.delivery import Delivery
from app.helpers.email_service import EmailService
from app.helpers.validators import (
    DeliveryValidator,
    handle_validation_error, 
    validate_json_body,
    ValidationException
)
from app.helpers.pagination import PaginationHelper
from app.helpers.enums import UserRole, DeliveryStatus

logger = logging.getLogger(__name__)


# =====================================================
# ADMIN LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminLoginController(View):

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)

        try:
            user = User.objects.get(email=body.get("email"))
        except User.DoesNotExist:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not check_password(body.get("password"), user.password_hash):
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not user.is_active:
            return JsonResponse({"error": "Account inactive"}, status=401)

        if user.role != "ADMIN":
            return JsonResponse({"error": "Access denied. Admin role required."}, status=403)

        return JsonResponse({
            "message": "Admin login successful",
            "token": str(uuid.uuid4()),
            "admin": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "department": user.department
            }
        })


# =====================================================
# ADMIN USER MANAGEMENT
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminUserController(View):
    """
    Admin can view all users and filter by role
    """

    def get(self, request):
        try:
            # Get role filter from query params
            role_filter = request.GET.get('role')
            
            query = User.objects.all()
            if role_filter:
                query = query.filter(role=role_filter.upper())
            
            page, page_size = PaginationHelper.get_pagination_params(request)
            
            # Apply pagination to get the user objects for this page
            paginated_result = PaginationHelper.paginate_queryset(
                query.values('id'), page, page_size
            )
            
            # Get the actual user objects for this page
            user_ids = [item['id'] for item in paginated_result['data']]
            users = User.objects.filter(id__in=user_ids)
            
            # Build detailed user data
            data = []
            for user in users:
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "phone_number": user.phone_number,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                
                # Add role-specific details
                if user.role == "END_USER":
                    user_data.update({
                        "address_line_1": user.address_line_1,
                        "address_line_2": user.address_line_2,
                        "city": user.city,
                        "state": user.state,
                        "postal_code": user.postal_code,
                        "country": user.country,
                        "delivery_notes": user.delivery_notes,
                    })
                elif user.role == "DELIVERY_PARTNER":
                    user_data.update({
                        "license_number": user.license_number,
                        "vehicle_type": user.vehicle_type,
                        "vehicle_number": user.vehicle_number,
                        "is_verified": user.is_verified,
                        "rating": user.rating,
                        "total_deliveries": user.total_deliveries,
                    })
                elif user.role == "ADMIN":
                    user_data.update({
                        "department": user.department,
                    })
                
                data.append(user_data)

            return JsonResponse({
                "users": data,
                "pagination": paginated_result['pagination'],
                "role_filter": role_filter
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# ADMIN DELIVERY MANAGEMENT
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminDeliveryController(View):
    """
    Admin can view all deliveries and assign delivery partners
    """

    def get(self, request):
        try:
            deliveries = Delivery.objects.all()
            
            page, page_size = PaginationHelper.get_pagination_params(request)
            
            # Apply pagination to get delivery IDs for this page
            paginated_result = PaginationHelper.paginate_queryset(
                deliveries.values('id'), page, page_size
            )
            
            # Get the actual delivery objects for this page
            delivery_ids = [item['id'] for item in paginated_result['data']]
            paginated_deliveries = Delivery.objects.filter(id__in=delivery_ids)

            data = []
            for delivery in paginated_deliveries:
                delivery_data = {
                    "id": delivery.id,
                    "tracking_number": delivery.tracking_number,
                    "pickup_address": delivery.pickup_address,
                    "delivery_address": delivery.delivery_address,
                    "item_description": delivery.item_description,
                    "status": delivery.status,
                    "delivery_fee": float(delivery.delivery_fee) if delivery.delivery_fee else None,
                    "pickup_notes": delivery.pickup_notes,
                    "delivery_notes": delivery.delivery_notes,
                    "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
                    "pickup_time": delivery.pickup_time.isoformat() if delivery.pickup_time else None,
                    "delivery_time": delivery.delivery_time.isoformat() if delivery.delivery_time else None,
                }
                
                # Get related users manually
                end_user = User.objects.filter(id=delivery.end_user_id).first() if delivery.end_user_id else None
                delivery_partner = User.objects.filter(id=delivery.delivery_partner_id).first() if delivery.delivery_partner_id else None
                
                delivery_data["end_user"] = {
                    "id": end_user.id,
                    "name": end_user.name,
                    "email": end_user.email,
                    "phone_number": end_user.phone_number
                } if end_user else None
                
                delivery_data["delivery_partner"] = {
                    "id": delivery_partner.id,
                    "name": delivery_partner.name,
                    "email": delivery_partner.email,
                    "phone_number": delivery_partner.phone_number,
                    "vehicle_type": delivery_partner.vehicle_type,
                    "vehicle_number": delivery_partner.vehicle_number
                } if delivery_partner else None
                
                data.append(delivery_data)

            return JsonResponse({
                "deliveries": data,
                "pagination": paginated_result['pagination']
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    @handle_validation_error
    def put(self, request, delivery_id):
        """
        Assign delivery partner to a delivery
        """
        body = validate_json_body(request)
        
        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return JsonResponse({"error": "Delivery not found"}, status=404)

        delivery_partner_id = body.get("delivery_partner_id")
        if not delivery_partner_id:
            return JsonResponse({"error": "delivery_partner_id is required"}, status=400)
        
        # Validate delivery_partner_id is a positive integer
        if not isinstance(delivery_partner_id, int) or delivery_partner_id <= 0:
            return JsonResponse({"error": "Invalid delivery_partner_id"}, status=400)

        # Verify delivery partner exists and is verified
        try:
            delivery_partner = User.objects.get(
                id=delivery_partner_id,
                role="DELIVERY_PARTNER",
                is_verified=True,
                is_active=True
            )
        except User.DoesNotExist:
            return JsonResponse({"error": "Valid delivery partner not found"}, status=404)

        try:
            with transaction.atomic():
                # Update delivery
                delivery.delivery_partner_id = delivery_partner_id
                delivery.status = "ASSIGNED"
                delivery.save()

                # Get end user for email
                end_user = User.objects.filter(id=delivery.end_user_id).first() if delivery.end_user_id else None

                # Send email notification to delivery partner
                try:
                    EmailService.send_delivery_assigned_to_partner({
                        'tracking_number': delivery.tracking_number,
                        'pickup_address': delivery.pickup_address,
                        'delivery_address': delivery.delivery_address,
                        'item_description': delivery.item_description,
                        'customer_name': end_user.name if end_user else 'N/A',
                        'customer_phone': end_user.phone_number if end_user else 'N/A',
                        'delivery_fee': float(delivery.delivery_fee) if delivery.delivery_fee else None,
                        'assigned_at': timezone.now().isoformat()
                    }, {
                        'name': delivery_partner.name,
                        'email': delivery_partner.email
                    })
                except Exception as e:
                    logger.error(f"Failed to send delivery assignment email: {str(e)}")

                return JsonResponse({
                    "message": "Delivery partner assigned successfully",
                    "delivery": {
                        "id": delivery.id,
                        "tracking_number": delivery.tracking_number,
                        "status": delivery.status,
                        "delivery_partner": {
                            "id": delivery_partner.id,
                            "name": delivery_partner.name,
                            "email": delivery_partner.email,
                            "vehicle_type": delivery_partner.vehicle_type,
                            "vehicle_number": delivery_partner.vehicle_number
                        }
                    }
                })
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# ADMIN DELIVERY PARTNER LIST
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminDeliveryPartnerController(View):
    """
    Get available delivery partners for assignment
    """

    def get(self, request):
        try:
            # Get all delivery partners (verified and unverified)
            delivery_partners = User.objects.filter(
                role="DELIVERY_PARTNER",
                is_active=True
            )

            data = []
            for partner in delivery_partners:
                data.append({
                    "id": partner.id,
                    "name": partner.name,
                    "email": partner.email,
                    "phone_number": partner.phone_number,
                    "vehicle_type": partner.vehicle_type,
                    "vehicle_number": partner.vehicle_number,
                    "rating": partner.rating,
                    "total_deliveries": partner.total_deliveries,
                    "license_number": partner.license_number,
                    "is_active": partner.is_active,
                    "is_verified": partner.is_verified,
                    "created_at": partner.created_at.isoformat() if partner.created_at else None
                })

            return JsonResponse({
                "delivery_partners": data,
                "count": len(data)
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    @handle_validation_error
    def put(self, request, partner_id):
        """
        Verify or unverify a delivery partner
        """
        body = validate_json_body(request)
        
        try:
            # Find delivery partner
            partner = User.objects.get(
                id=partner_id,
                role="DELIVERY_PARTNER"
            )
            
        except User.DoesNotExist:
            return JsonResponse({"error": "Delivery partner not found"}, status=404)
        
        # Validate is_verified field
        is_verified = body.get("is_verified")
        if is_verified is None:
            return JsonResponse({"error": "is_verified field is required"}, status=400)
        
        if not isinstance(is_verified, bool):
            return JsonResponse({"error": "is_verified must be a boolean value"}, status=400)
        
        # Update verification status
        partner.is_verified = is_verified
        partner.save()
        
        # Send verification email to partner
        try:
            EmailService.send_partner_verification_email({
                'name': partner.name,
                'email': partner.email,
                'is_verified': is_verified,
                'updated_at': partner.updated_at.isoformat() if partner.updated_at else None
            })
        except Exception as e:
            logger.error(f"Failed to send verification email to partner: {str(e)}")
        
        status = "verified" if is_verified else "unverified"
        partner_data = {
            "id": partner.id,
            "name": partner.name,
            "email": partner.email,
            "is_verified": partner.is_verified
        }
        
        return JsonResponse({
            "message": f"Delivery partner {status} successfully",
            "partner": partner_data
        })
