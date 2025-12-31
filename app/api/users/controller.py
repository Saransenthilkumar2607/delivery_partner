import json
import uuid
import logging
from functools import wraps
from datetime import datetime

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction, DatabaseError
from django.core.exceptions import ValidationError as DjangoValidationError

from app.models.users import User
from app.models.delivery import Delivery

from app.helpers.validators import (
    UserValidator,
    DeliveryValidator,
    validate_json_body
)
from app.helpers.pagination import PaginationHelper
from app.helpers.redis_service import RedisService
from app.helpers.email_service import EmailService
from app.helpers.exceptions import (
    APIError, BadRequestError, NotFoundError,
    ConflictError, ValidationError
)

logger = logging.getLogger(__name__)

# =====================================================
# COMMON DECORATOR
# =====================================================

def handle_validation_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return JsonResponse({"errors": e.errors}, status=400)
        except BadRequestError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except NotFoundError as e:
            return JsonResponse({"error": str(e)}, status=404)
        except ConflictError as e:
            return JsonResponse({"error": str(e)}, status=409)
        except Exception as e:
            logger.exception(e)
            return JsonResponse(
                {"error": "Internal server error"},
                status=500
            )
    return wrapper


# =====================================================
# USERS LIST & CREATE
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserListController(View):

    def get(self, request):
        try:
            page, page_size = PaginationHelper.get_pagination_params(request)
            cache_key = f"users_list:{page}:{page_size}"

            cached = RedisService.get_cached_query_result(cache_key)
            if cached:
                return JsonResponse(cached)

            users_qs = User.objects.all().values(
                "id", "email", "name", "role",
                "is_active", "created_at"
            )

            if not users_qs.exists():
                raise NotFoundError("No users found")

            result = PaginationHelper.paginate_queryset(
                users_qs, page, page_size
            )

            response = {
                "status": "success",
                "data": {
                    "users": result["data"],
                    "pagination": result["pagination"]
                }
            }

            RedisService.cache_query_result(
                cache_key, response, timeout=300
            )

            return JsonResponse(response)

        except Exception as e:
            logger.exception(e)
            return JsonResponse(
                {"error": "Failed to fetch users"},
                status=500
            )

    def post(self, request):
        try:
            body = validate_json_body(request)
            validated = UserValidator.validate_user_creation(
                body, body.get("role", "END_USER")
            )

            if User.objects.filter(email=validated["email"]).exists():
                raise ConflictError("Email already exists")

            with transaction.atomic():
                user = User.objects.create(
                    email=validated["email"],
                    name=validated["name"],
                    password_hash=make_password(validated["password"]),
                    role=validated["role"],
                    phone_number=validated.get("phone_number"),
                    address_line_1=validated.get("address_line_1"),
                    address_line_2=validated.get("address_line_2"),
                    city=validated.get("city"),
                    state=validated.get("state"),
                    postal_code=validated.get("postal_code"),
                    country=validated.get("country", "india"),
                    delivery_notes=validated.get("delivery_notes"),
                    license_number=validated.get("license_number"),
                    vehicle_type=validated.get("vehicle_type"),
                    vehicle_number=validated.get("vehicle_number"),
                    department=validated.get("department"),
                )

            try:
                EmailService.send_welcome_email_to_user({
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                })
            except Exception as e:
                logger.error(f"Email failed: {e}")

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

        except DjangoValidationError as e:
            return JsonResponse(e.message_dict, status=400)
        except Exception as e:
            logger.exception(e)
            return JsonResponse(
                {"error": "User creation failed"},
                status=500
            )


# =====================================================
# USER DETAIL
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserDetailController(View):

    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        return JsonResponse({
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
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
                "department": user.department,
            }
        })

    @handle_validation_error
    def put(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFoundError("User not found")

        body = validate_json_body(request)

        allowed_fields = [
            "name", "phone_number",
            "address_line_1", "address_line_2",
            "city", "state", "postal_code",
            "delivery_notes", "department"
        ]

        for field in allowed_fields:
            if field in body:
                setattr(user, field, body[field])

        user.updated_at = datetime.utcnow()
        user.save()

        return JsonResponse({"message": "User updated successfully"})

    def delete(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user.delete()
        return JsonResponse({"message": "User deleted successfully"})


# =====================================================
# LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class UserLoginController(View):

    @handle_validation_error
    def post(self, request):
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        if not RedisService.rate_limit_check(
            f"login:{client_ip}", limit=5, window=60
        ):
            return JsonResponse(
                {"error": "Too many login attempts"},
                status=429
            )

        body = validate_json_body(request)
        validated = UserValidator.validate_login(body)

        try:
            user = User.objects.get(email=validated["email"])
        except User.DoesNotExist:
            raise ValidationError({"email": "User not found"})

        if not check_password(validated["password"], user.password_hash):
            raise ValidationError({"password": "Invalid password"})

        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active
        }

        RedisService.cache_user_data(user.id, user_data, timeout=1800)

        return JsonResponse({
            "message": "Login successful",
            "user": user_data
        })


# =====================================================
# DELIVERY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryController(View):

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)
        validated = DeliveryValidator.validate_delivery_creation(body)

        tracking_number = f"TRK{uuid.uuid4().hex[:12].upper()}"

        delivery = Delivery.objects.create(
            tracking_number=tracking_number,
            end_user_id=validated["end_user_id"],
            pickup_address=validated["pickup_address"],
            delivery_address=validated["delivery_address"],
            item_description=validated["item_description"],
            delivery_fee=validated.get("delivery_fee"),
            tip=validated.get("tip"),
            pickup_notes=validated.get("pickup_notes"),
            delivery_notes=validated.get("delivery_notes"),
        )

        return JsonResponse({
            "message": "Delivery created successfully",
            "delivery": {
                "id": delivery.id,
                "tracking_number": delivery.tracking_number,
                "status": delivery.status,
                "created_at": delivery.created_at.isoformat()
            }
        }, status=201)

    def get(self, request):
        user_id = request.GET.get("user_id")

        qs = Delivery.objects.all()
        if user_id:
            qs = qs.filter(end_user_id=user_id)

        deliveries = qs.values(
            "id", "tracking_number", "status",
            "pickup_address", "delivery_address",
            "item_description", "created_at"
        )

        return JsonResponse({
            "count": deliveries.count(),
            "deliveries": list(deliveries)
        })
