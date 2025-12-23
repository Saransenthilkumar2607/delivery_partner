import json
import uuid
import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password, check_password

from app.models.users import User
from app.models.delivery import Delivery
from app.helpers.enums import UserRole, DeliveryStatus
from app.helpers.email_service import EmailService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# Create SQLAlchemy session
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
        try:
            session = SessionLocal()
            users = session.query(User).all()
            data = []

            for user in users:
                data.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_active": user.is_active,
                    "phone_number": user.phone_number,
                })
            
            session.close()

            return JsonResponse({
                "users": data,
                "count": len(data)
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def post(self, request):
        try:
            body = json.loads(request.body)
            session = SessionLocal()

            required_fields = ["email", "name", "password", "role"]
            for field in required_fields:
                if field not in body:
                    return JsonResponse(
                        {"error": f"{field} is required"},
                        status=400
                    )

            if session.query(User).filter(User.email == body["email"]).first():
                session.close()
                return JsonResponse(
                    {"error": "Email already exists"},
                    status=400
                )

            user = User(
                email=body["email"],
                name=body["name"],
                password_hash=make_password(body["password"]),
                role=body["role"],
                phone_number=body.get("phone_number"),
                address_line_1=body.get("address_line_1"),
                address_line_2=body.get("address_line_2"),
                city=body.get("city"),
                state=body.get("state"),
                postal_code=body.get("postal_code"),
                country=body.get("country", "india"),
                delivery_notes=body.get("delivery_notes"),
                license_number=body.get("license_number"),
                vehicle_type=body.get("vehicle_type"),
                vehicle_number=body.get("vehicle_number"),
                department=body.get("department"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            session.close()

            return JsonResponse({
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role
                }
            }, status=201)

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


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

    def put(self, request, user_id):
        try:
            session = SessionLocal()
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                session.close()
                return JsonResponse({"error": "User not found"}, status=404)

            body = json.loads(request.body)

            for field in body:
                if hasattr(user, field):
                    setattr(user, field, body[field])
            
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

    def post(self, request):
        try:
            body = json.loads(request.body)
            session = SessionLocal()

            user = session.query(User).filter(User.email == body.get("email")).first()
            if not user:
                session.close()
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            if not check_password(body.get("password"), user.password_hash):
                session.close()
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            if not user.is_active:
                session.close()
                return JsonResponse({"error": "Account inactive"}, status=401)

            token = str(uuid.uuid4())
            session.close()

            return JsonResponse({
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                }
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# DELIVERY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryController(View):

    def post(self, request):
        try:
            body = json.loads(request.body)
            session = SessionLocal()

            required = ["pickup_address", "delivery_address", "item_description", "end_user_id"]
            for field in required:
                if field not in body:
                    return JsonResponse(
                        {"error": f"{field} is required"},
                        status=400
                    )

            # Verify that the end_user_id belongs to an END_USER role
            end_user = session.query(User).filter(User.id == body["end_user_id"]).first()
            if not end_user:
                session.close()
                return JsonResponse({"error": "End user not found"}, status=404)

            if end_user.role != UserRole.END_USER:
                session.close()
                return JsonResponse({"error": "Only END_USER role can create deliveries"}, status=403)

            delivery = Delivery(
                tracking_number=f"DEL{uuid.uuid4().hex[:8].upper()}",
                end_user_id=body["end_user_id"],
                pickup_address=body["pickup_address"],
                delivery_address=body["delivery_address"],
                item_description=body["item_description"],
                delivery_fee=body.get("delivery_fee"),
                pickup_notes=body.get("pickup_notes"),
                delivery_notes=body.get("delivery_notes"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            session.add(delivery)
            session.commit()
            session.refresh(delivery)
            
            # Send email notification to admin about new order
            delivery_details = {
                'tracking_number': delivery.tracking_number,
                'pickup_address': delivery.pickup_address,
                'delivery_address': delivery.delivery_address,
                'item_description': delivery.item_description,
                'customer_name': end_user.name,
                'customer_email': end_user.email,
                'customer_phone': end_user.phone_number,
                'created_at': delivery.created_at.isoformat() if delivery.created_at else None
            }
            EmailService.send_order_created_to_admin(delivery_details)
            
            session.close()

            return JsonResponse({
                "message": "Delivery created successfully",
                "delivery": {
                    "id": delivery.id,
                    "tracking_number": delivery.tracking_number,
                    "status": delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status),
                }
            }, status=201)

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def get(self, request):
        try:
            session = SessionLocal()
            deliveries = session.query(Delivery).filter(Delivery.end_user_id == 1).all()

            data = []
            for d in deliveries:
                data.append({
                    "id": d.id,
                    "tracking_number": d.tracking_number,
                    "pickup_address": d.pickup_address,
                    "delivery_address": d.delivery_address,
                    "item_description": d.item_description,
                    "status": d.status.value if hasattr(d.status, 'value') else str(d.status),
                    "delivery_fee": float(d.delivery_fee) if d.delivery_fee else None,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                })
            
            session.close()

            return JsonResponse({
                "deliveries": data,
                "count": len(data)
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)
