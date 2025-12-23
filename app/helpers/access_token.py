from functools import wraps
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import jwt
import logging

from app.helpers.redis_client import redis_client

logger = logging.getLogger(__name__)

User = get_user_model()


# ======================================================
# TOKEN GENERATION
# ======================================================

def generate_access_token(user):
    payload = {
        "user_id": user.id,
        "role": user.role,
        "type": "access",
        "exp": timezone.now() + timedelta(days=settings.JWT_ACCESS_TOKEN_EXP_DAYS),
        "iat": timezone.now(),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user):
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "exp": timezone.now() + timedelta(
            minutes=settings.JWT_REFRESH_TOKEN_EXP_MINUTES
        ),
        "iat": timezone.now(),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    # Store refresh token in Redis
    redis_key = f"refresh_token:{user.id}"
    redis_client.setex(
        redis_key,
        settings.JWT_REFRESH_TOKEN_EXP_MINUTES * 60,
        token
    )

    return token


# ======================================================
# TOKEN HELPERS
# ======================================================

def decode_jwt_token(token):
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_request(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    parts = auth_header.split(" ")

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


# ======================================================
# AUTHENTICATION
# ======================================================

def authenticate_request(request):
    token = get_token_from_request(request)

    if not token:
        return None

    payload = decode_jwt_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("user_id")

    try:
        user = User.objects.get(id=user_id, is_active=True)
        request.user = user
        return user
    except User.DoesNotExist:
        return None


# ======================================================
# REFRESH TOKEN LOGIC
# ======================================================

def refresh_access_token(refresh_token):
    payload = decode_jwt_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        return None

    user_id = payload.get("user_id")
    redis_key = f"refresh_token:{user_id}"

    stored_token = redis_client.get(redis_key)

    if not stored_token or stored_token != refresh_token:
        return None

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return None

    new_access_token = generate_access_token(user)
    return new_access_token


# ======================================================
# AUTHORIZATION DECORATORS
# ======================================================

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = authenticate_request(request)

        if not user:
            return JsonResponse(
                {"message": "Authentication required"},
                status=401
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = authenticate_request(request)

            if not user:
                return JsonResponse(
                    {"message": "Authentication required"},
                    status=401
                )

            if user.role not in allowed_roles:
                return JsonResponse(
                    {"message": "Permission denied"},
                    status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# ======================================================
# OPTIONAL HELPERS
# ======================================================

def is_admin(user):
    return getattr(user, "role", None) == "ADMIN"


def is_delivery_partner(user):
    return getattr(user, "role", None) == "DELIVERY_PARTNER"


def is_end_user(user):
    return getattr(user, "role", None) == "USER"
