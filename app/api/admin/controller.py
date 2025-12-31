import json
import uuid
import logging
from functools import wraps

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction, DatabaseError
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from app.models.users import User
from app.models.delivery import Delivery
from app.helpers.email_service import EmailService
from app.helpers.validators import (
    DeliveryValidator,
    validate_json_body
)
from app.helpers.pagination import PaginationHelper
from app.helpers.redis_service import RedisService
from app.helpers.exceptions import (
    APIError, BadRequestError, UnauthorizedError, ForbiddenError, 
    NotFoundError, ConflictError, ValidationError, DatabaseError as DBError
)
from app.helpers.enums import UserRole, DeliveryStatus

logger = logging.getLogger(__name__)


# =====================================================
# ADMIN LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminLoginController(View):

    def post(self, request):
        try:
            body = validate_json_body(request)
            email = body.get("email")
            password = body.get("password")
            
            if not email or not password:
                raise BadRequestError("Email and password are required")

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise UnauthorizedError("Invalid credentials")

            if not check_password(password, user.password_hash):
                raise UnauthorizedError("Invalid credentials")

            if not user.is_active:
                raise UnauthorizedError("Account is inactive")

            if user.role != UserRole.ADMIN:
                raise ForbiddenError("Access denied. Admin privileges required.")

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

        except Exception as e:
            if not isinstance(e, APIError):
                logger.error(f"Error in AdminLoginController.post: {str(e)}")
                raise APIError("Failed to login") from e
            raise


# =====================================================
# ADMIN USER MANAGEMENT
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminUserController(View):
    """
    Admin can view all users with filtering and pagination
    """

    def get(self, request):
        try:
            from django.db.models import Q
            
            # Get query parameters
            role_filter = request.GET.get('role')
            search = request.GET.get('search', '').strip()
            
            # Start building the query - ordered by created_at ascending (oldest first)
            users = User.objects.all().order_by('created_at')
            
            # Apply filters
            if role_filter:
                users = users.filter(role=role_filter.upper())
                
            if search:
                users = users.filter(
                    Q(email__icontains=search) | 
                    Q(name__icontains=search) |
                    Q(phone_number__icontains=search)
                )
            
            # Apply pagination
            result = PaginationHelper.paginate_queryset(
                queryset=users,
                request=request
            )
            
            # Format user data
            users_data = []
            for user in result['data']:
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name or "",
                    "role": user.role,
                    "is_active": user.is_active,
                    "phone_number": user.phone_number or "",
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                
                # Add role-specific fields
                if hasattr(user, 'address_line_1'):
                    user_data.update({
                        "address": {
                            "line1": user.address_line_1 or "",
                            "line2": user.address_line_2 or "",
                            "city": user.city or "",
                            "state": user.state or "",
                            "postal_code": user.postal_code or "",
                            "country": user.country or ""
                        }
                    })
                
                users_data.append(user_data)
            
            # Build response
            response_data = {
                "success": True,
                "users": users_data,
                "pagination": result.get('pagination'),
                "filters": {
                    "role": role_filter,
                    "search": search if search else None
                }
            }
            
            return JsonResponse(response_data, safe=False)
            
        except Exception as e:
            logger.error(f"Error in AdminUserController.get: {str(e)}", exc_info=True)
            from app.helpers.exceptions import APIError
            return JsonResponse({
                "success": False,
                "error": "Failed to fetch users",
                "details": str(e)
            }, status=500)


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
            if not isinstance(e, APIError):
                logger.error(f"Error in AdminDeliveryController.get: {str(e)}")
                raise APIError("Failed to retrieve deliveries") from e
            raise

    def put(self, request, delivery_id):
        """
        Assign delivery partner to a delivery
        """
        try:
            body = validate_json_body(request)
            delivery_partner_id = body.get("delivery_partner_id")
            
            if not delivery_partner_id:
                raise BadRequestError("Delivery partner ID is required")
            
            with transaction.atomic():
                # Find delivery and delivery partner
                try:
                    delivery = Delivery.objects.select_for_update().get(id=delivery_id)
                    delivery_partner = User.objects.get(
                        id=delivery_partner_id,
                        role=UserRole.DELIVERY_PARTNER
                    )
                except Delivery.DoesNotExist:
                    raise NotFoundError("Delivery not found")
                except User.DoesNotExist:
                    raise NotFoundError("Delivery partner not found")
                
                # Update delivery
                delivery.delivery_partner_id = delivery_partner_id
                delivery.status = DeliveryStatus.ASSIGNED
                
                try:
                    delivery.save()
                except DatabaseError as e:
                    logger.error(f"Database error updating delivery: {str(e)}")
                    raise DBError("Failed to update delivery") from e
                
                # Invalidate relevant caches
                RedisService.invalidate_query_cache("admin_deliveries")
                
                return JsonResponse({
                    "status": "success",
                    "message": "Delivery partner assigned successfully",
                    "data": {
                        "delivery": {
                            "id": delivery.id,
                            "status": delivery.status,
                            "delivery_partner": {
                                "id": delivery_partner.id,
                                "name": delivery_partner.name,
                                "email": delivery_partner.email
                            }
                        }
                    }
                })
                
        except DjangoValidationError as e:
            raise ValidationError(errors=e.message_dict)
        except Exception as e:
            if not isinstance(e, APIError):
                logger.error(f"Error in AdminDeliveryController.put: {str(e)}")
                raise APIError("Failed to assign delivery partner") from e
            raise


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
            cache_key = "delivery_partners:active"
            
            # Try to get from cache first
            cached_result = RedisService.get_cached_query_result(cache_key)
            if cached_result:
                return JsonResponse({
                    "status": "success",
                    "data": cached_result
                })
            
            # Only return active delivery partners
            delivery_partners = User.objects.filter(
                role=UserRole.DELIVERY_PARTNER,
                is_active=True
            ).values('id', 'name', 'email', 'phone_number', 'is_verified')
            
            response_data = {
                "status": "success",
                "data": {
                    "delivery_partners": list(delivery_partners)
                }
            }
            
            # Cache the result for 5 minutes
            RedisService.cache_query_result(cache_key, response_data['data'], timeout=300)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            if not isinstance(e, APIError):
                logger.error(f"Error in AdminDeliveryPartnerController.get: {str(e)}")
                raise APIError("Failed to retrieve delivery partners") from e
            raise

    def put(self, request, partner_id):
        """
        Verify or unverify a delivery partner
        """
        try:
            body = validate_json_body(request)
            is_verified = body.get('is_verified')
            
            if is_verified is None:
                raise BadRequestError("is_verified field is required")
                
            with transaction.atomic():
                try:
                    partner = User.objects.select_for_update().get(
                        id=partner_id,
                        role=UserRole.DELIVERY_PARTNER
                    )
                except User.DoesNotExist:
                    raise NotFoundError("Delivery partner not found")
                
                partner.is_verified = is_verified
                
                try:
                    partner.save()
                except DatabaseError as e:
                    logger.error(f"Database error updating delivery partner: {str(e)}")
                    raise DBError("Failed to update delivery partner") from e
                
                # Invalidate relevant caches
                RedisService.invalidate_query_cache("delivery_partners")
                
                return JsonResponse({
                    "status": "success",
                    "message": f"Delivery partner {'verified' if is_verified else 'unverified'} successfully",
                    "data": {
                        "delivery_partner": {
                            "id": partner.id,
                            "name": partner.name,
                            "email": partner.email,
                            "is_verified": partner.is_verified
                        }
                    }
                })
                
        except DjangoValidationError as e:
            raise ValidationError(errors=e.message_dict)
        except Exception as e:
            if not isinstance(e, APIError):
                logger.error(f"Error in AdminDeliveryPartnerController.put: {str(e)}")
                raise APIError("Failed to update delivery partner") from e
            raise
            {"is_verified": partner.is_verified}

        
        
        return JsonResponse({
            "message": f"Delivery partner {status} successfully",
            "partner": partner_data
        })
