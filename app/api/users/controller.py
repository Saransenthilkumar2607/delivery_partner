import json
import uuid
import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction

from app.models.users import User
from app.models.delivery import Delivery
from app.helpers.validators import (
    UserValidator,
    DeliveryValidator,
    handle_validation_error,
    validate_json_body
)
from app.helpers.pagination import PaginationHelper
from app.helpers.redis_service import RedisService
from app.helpers.database import get_database_session

logger = logging.getLogger(__name__)


# =====================================================
# USERS
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserListController(View):
    """
    GET  -> list users
    POST -> create user
    """

    def get(self, request):
        """Get all users with pagination and caching"""
        # Generate cache key based on pagination parameters
        page, page_size = PaginationHelper.get_pagination_params(request)
        cache_key = f"users_list:page_{page}:size_{page_size}"
        
        # Try to get from cache first
        cached_result = RedisService.get_cached_query_result(cache_key)
        if cached_result:
            return JsonResponse(cached_result)
        
        # If not in cache, query database
        users_queryset = User.objects.all().values('id', 'email', 'name', 'role', 'is_active', 'created_at')
        
        result = PaginationHelper.paginate_queryset(users_queryset, page, page_size)
        
        response_data = {
            "users": result['data'],
            "pagination": result['pagination']
        }
        
        # Cache the result for 5 minutes
        RedisService.cache_query_result(cache_key, response_data, timeout=300)
        
        return JsonResponse(response_data)

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)
        validated_data = UserValidator.validate_user_creation(body, body.get("role", "END_USER"))

        with transaction.atomic():
            # Check if email already exists
            if User.objects.filter(email=validated_data["email"]).exists():
                return JsonResponse(
                    {"error": "Email already exists"},
                    status=400
                )

            # Create user
            user = User.objects.create(
                email=validated_data["email"],
                name=validated_data["name"],
                password_hash=make_password(validated_data["password"]),
                role=validated_data["role"],
                phone_number=validated_data.get("phone_number"),
                address_line_1=validated_data.get("address_line_1"),
                address_line_2=validated_data.get("address_line_2"),
                city=validated_data.get("city"),
                state=validated_data.get("state"),
                postal_code=validated_data.get("postal_code"),
                country=validated_data.get("country", "india"),
                delivery_notes=validated_data.get("delivery_notes"),
                license_number=validated_data.get("license_number"),
                vehicle_type=validated_data.get("vehicle_type"),
                vehicle_number=validated_data.get("vehicle_number"),
                department=validated_data.get("department"),
            )

            # Send welcome email to user
            try:
                logger.info(f"About to send welcome email to user. Email: '{user.email}', User object: {user}")
                EmailService.send_welcome_email_to_user({
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })
            except Exception as e:
                logger.error(f"Failed to send welcome email to user: {str(e)}")

            # Invalidate user list cache when new user is created
            RedisService.invalidate_query_cache("users_list")

            return JsonResponse({
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role
                }
            }, status=201)


# =====================================================
# USER DETAIL
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserDetailController(View):
    """
    GET    -> retrieve user
    PUT    -> update user
    DELETE -> delete user
    """

    def get(self, request, user_id):
        try:
            session = SessionLocal()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                session.close()
                return JsonResponse({"error": "User not found"}, status=404)

            result = {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_active": user.is_active,
                    "phone_number": user.phone_number,
                    "address_line_1": user.address_line_1,
                    "address_line_2": user.address_line_2,
                    "city": user.city,
                    "state": user.state,
                    "postal_code": user.postal_code,
                    "country": user.country,
                    "delivery_notes": user.delivery_notes,
                    "license_number": user.license_number,
                    "vehicle_type": user.vehicle_type,
                    "vehicle_number": user.vehicle_number,
                    "is_verified": user.is_verified,
                    "rating": user.rating,
                    "total_deliveries": user.total_deliveries,
                    "department": user.department,
                }
            }
            session.close()
            return result

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    @handle_validation_error
    def put(self, request, user_id):
        try:
            session = SessionLocal()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                session.close()
                return JsonResponse({"error": "User not found"}, status=404)

            body = validate_json_body(request)
            
            # Validate update data based on user role
            if user.role == UserRole.DELIVERY_PARTNER:
                validated_data = DeliveryPartnerValidator.validate_profile_update(body)
            elif user.role == UserRole.END_USER:
                # For end users, validate address fields
                validated_data = {}
                address_fields = ["address_line_1", "address_line_2", "city", "state", "postal_code", "delivery_notes"]
                for field in address_fields:
                    if field in body:
                        value = body[field]
                        if value is not None:
                            validated_data[field] = str(value).strip()
                
                # Validate phone number if provided
                if "phone_number" in body:
                    phone_data = {"phone_number": body["phone_number"]}
                    phone_validated = DeliveryPartnerValidator.validate_profile_update(phone_data)
                    validated_data.update(phone_validated)
            else:
                # Admin users - limited fields
                validated_data = {}
                allowed_fields = ["name", "phone_number", "department"]
                for field in allowed_fields:
                    if field in body:
                        validated_data[field] = body[field]

            for field, value in validated_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.close()

            return JsonResponse({"message": "User updated successfully"})

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def delete(self, request, user_id):
        try:
            session = SessionLocal()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                session.close()
                return JsonResponse({"error": "User not found"}, status=404)

            session.delete(user)
            session.commit()
            session.close()
            return JsonResponse({"message": "User deleted successfully"})

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserLoginController(View):
    """
    User login endpoint
    """

    @handle_validation_error
    def post(self, request):
        # Rate limiting: 5 login attempts per minute per IP
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        if not RedisService.rate_limit_check(f"login:{client_ip}", limit=5, window=60):
            return JsonResponse({
                "error": "Too many login attempts. Please try again later."
            }, status=429)
        
        body = validate_json_body(request)
        validated_data = UserValidator.validate_login(body)

        try:
            user = User.objects.get(email=validated_data["email"])
            
            if check_password(validated_data["password"], user.password_hash):
                # Cache user data for quick access
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "is_active": user.is_active
                }
                RedisService.cache_user_data(user.id, user_data, timeout=1800)  # 30 minutes
                
                return JsonResponse({
                    "message": "Login successful",
                    "user": user_data
                })
            else:
                raise ValidationException({
                    "password": "Invalid password"
                })

        except User.DoesNotExist:
            raise ValidationException({
                "email": "User not found"
            })


# =====================================================
# DELIVERY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryController(View):

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)
        validated_data = DeliveryValidator.validate_delivery_creation(body)

        with transaction.atomic():
            # Generate tracking number
            tracking_number = f"TRK{uuid.uuid4().hex[:12].upper()}"

            # Create delivery
            delivery = Delivery.objects.create(
                tracking_number=tracking_number,
                end_user_id=validated_data["end_user_id"],
                pickup_address=validated_data["pickup_address"],
                delivery_address=validated_data["delivery_address"],
                item_description=validated_data["item_description"],
                delivery_fee=validated_data.get("delivery_fee"),
                tip=validated_data.get("tip"),
                pickup_notes=validated_data.get("pickup_notes"),
                delivery_notes=validated_data.get("delivery_notes")
            )

            # Get end user for email
            end_user = User.objects.get(id=delivery.end_user_id)

            # Send email to admin
            try:
                EmailService.send_order_created_to_admin({
                    'tracking_number': delivery.tracking_number,
                    'pickup_address': delivery.pickup_address,
                    'delivery_address': delivery.delivery_address,
                    'item_description': delivery.item_description,
                    'delivery_fee': float(delivery.delivery_fee) if delivery.delivery_fee else 0,
                    'tip': float(delivery.tip) if delivery.tip else 0,
                    'customer_name': end_user.name if end_user else 'Unknown',
                    'customer_email': end_user.email if end_user else 'Unknown',
                    'created_at': delivery.created_at.isoformat() if delivery.created_at else None
                })
            except Exception as e:
                logger.error(f"Failed to send order email to admin: {str(e)}")

            return JsonResponse({
                "message": "Delivery created successfully",
                "delivery": {
                    "id": delivery.id,
                    "tracking_number": delivery.tracking_number,
                    "status": delivery.status,
                    "created_at": delivery.created_at.isoformat() if delivery.created_at else None
                }
            }, status=201)

    def get(self, request):
        """Get user's deliveries"""
        user_id = request.GET.get('user_id')
        
        if user_id:
            deliveries = Delivery.objects.filter(end_user_id=user_id).values(
                'id', 'tracking_number', 'status', 'pickup_address', 'delivery_address', 
                'item_description', 'created_at'
            )
        else:
            deliveries = Delivery.objects.all().values(
                'id', 'tracking_number', 'status', 'pickup_address', 'delivery_address', 
                'item_description', 'created_at'
            )

        return JsonResponse({
            "deliveries": list(deliveries),
            "count": deliveries.count()
        })
