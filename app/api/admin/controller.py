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
from app.helpers.validators import (
    DeliveryValidator,
    handle_validation_error, 
    validate_json_body,
    ValidationException
)
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
# ADMIN LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class AdminLoginController(View):

    @handle_validation_error
    def post(self, request):
        try:
            body = validate_json_body(request)
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

            if user.role.upper() != UserRole.ADMIN:
                session.close()
                return JsonResponse({"error": "Access denied. Admin role required."}, status=403)

            token = str(uuid.uuid4())
            session.close()

            return JsonResponse({
                "message": "Admin login successful",
                "token": token,
                "admin": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "department": user.department
                }
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


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
            session = SessionLocal()
            
            # Get role filter from query params
            role_filter = request.GET.get('role')
            
            query = session.query(User)
            if role_filter:
                query = query.filter(User.role == role_filter.upper())
            
            users = query.all()
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
                if user.role == UserRole.END_USER:
                    user_data.update({
                        "address_line_1": user.address_line_1,
                        "address_line_2": user.address_line_2,
                        "city": user.city,
                        "state": user.state,
                        "postal_code": user.postal_code,
                        "country": user.country,
                        "delivery_notes": user.delivery_notes,
                    })
                elif user.role == UserRole.DELIVERY_PARTNER:
                    user_data.update({
                        "license_number": user.license_number,
                        "vehicle_type": user.vehicle_type,
                        "vehicle_number": user.vehicle_number,
                        "is_verified": user.is_verified,
                        "rating": user.rating,
                        "total_deliveries": user.total_deliveries,
                    })
                elif user.role == UserRole.ADMIN:
                    user_data.update({
                        "department": user.department,
                    })
                
                data.append(user_data)
            
            session.close()

            return JsonResponse({
                "users": data,
                "count": len(data),
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
            session = SessionLocal()
            deliveries = session.query(Delivery).all()

            data = []
            for d in deliveries:
                # Get end user details
                end_user = session.query(User).filter(User.id == d.end_user_id).first()
                delivery_partner = None
                if d.delivery_partner_id:
                    delivery_partner = session.query(User).filter(User.id == d.delivery_partner_id).first()

                delivery_data = {
                    "id": d.id,
                    "tracking_number": d.tracking_number,
                    "pickup_address": d.pickup_address,
                    "delivery_address": d.delivery_address,
                    "item_description": d.item_description,
                    "status": d.status,
                    "delivery_fee": float(d.delivery_fee) if d.delivery_fee else None,
                    "pickup_notes": d.pickup_notes,
                    "delivery_notes": d.delivery_notes,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "pickup_time": d.pickup_time.isoformat() if d.pickup_time else None,
                    "delivery_time": d.delivery_time.isoformat() if d.delivery_time else None,
                    "end_user": {
                        "id": end_user.id,
                        "name": end_user.name,
                        "email": end_user.email,
                        "phone_number": end_user.phone_number
                    } if end_user else None,
                    "delivery_partner": {
                        "id": delivery_partner.id,
                        "name": delivery_partner.name,
                        "email": delivery_partner.email,
                        "phone_number": delivery_partner.phone_number,
                        "vehicle_type": delivery_partner.vehicle_type,
                        "vehicle_number": delivery_partner.vehicle_number
                    } if delivery_partner else None
                }
                data.append(delivery_data)
            
            session.close()

            return JsonResponse({
                "deliveries": data,
                "count": len(data)
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    @handle_validation_error
    def put(self, request, delivery_id):
        """
        Assign delivery partner to a delivery
        """
        try:
            body = validate_json_body(request)
            session = SessionLocal()

            delivery = session.query(Delivery).filter(Delivery.id == delivery_id).first()
            if not delivery:
                session.close()
                return JsonResponse({"error": "Delivery not found"}, status=404)

            delivery_partner_id = body.get("delivery_partner_id")
            if not delivery_partner_id:
                session.close()
                return JsonResponse({"error": "delivery_partner_id is required"}, status=400)
            
            # Validate delivery_partner_id is a positive integer
            if not isinstance(delivery_partner_id, int) or delivery_partner_id <= 0:
                session.close()
                return JsonResponse({"error": "Invalid delivery_partner_id"}, status=400)

            # Verify delivery partner exists and is verified
            delivery_partner = session.query(User).filter(
                User.id == delivery_partner_id,
                User.role == UserRole.DELIVERY_PARTNER,
                User.is_verified == True,
                User.is_active == True
            ).first()

            if not delivery_partner:
                session.close()
                return JsonResponse({"error": "Valid delivery partner not found"}, status=404)

            # Update delivery
            delivery.delivery_partner_id = delivery_partner_id
            delivery.status = DeliveryStatus.ASSIGNED
            delivery.updated_at = datetime.utcnow()
            delivery.pickup_time = datetime.utcnow()

            session.commit()
            
            # Get end user details for email
            end_user = session.query(User).filter(User.id == delivery.end_user_id).first()
            
            # Send email notification to delivery partner
            delivery_details = {
                'tracking_number': delivery.tracking_number,
                'pickup_address': delivery.pickup_address,
                'delivery_address': delivery.delivery_address,
                'item_description': delivery.item_description,
                'customer_name': end_user.name if end_user else 'N/A',
                'customer_phone': end_user.phone_number if end_user else 'N/A',
                'delivery_fee': float(delivery.delivery_fee) if delivery.delivery_fee else None,
                'assigned_at': delivery.pickup_time.isoformat() if delivery.pickup_time else None
            }
            
            partner_details = {
                'name': delivery_partner.name,
                'email': delivery_partner.email
            }
            
            EmailService.send_delivery_assigned_to_partner(delivery_details, partner_details)
            
            session.close()

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
            session = SessionLocal()
            
            # Get all delivery partners (verified and unverified)
            delivery_partners = session.query(User).filter(
                User.role == UserRole.DELIVERY_PARTNER,
                User.is_active == True
            ).all()

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
            
            session.close()

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
        try:
            body = validate_json_body(request)
            session = SessionLocal()
            
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)
            
            # Validate is_verified field
            is_verified = body.get("is_verified")
            if is_verified is None:
                session.close()
                return JsonResponse({"error": "is_verified field is required"}, status=400)
            
            if not isinstance(is_verified, bool):
                session.close()
                return JsonResponse({"error": "is_verified must be a boolean value"}, status=400)
            
            # Update verification status
            partner.is_verified = is_verified
            partner.updated_at = datetime.utcnow()
            
            session.commit()
            
            status = "verified" if is_verified else "unverified"
            partner_data = {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "is_verified": partner.is_verified
            }
            
            session.close()
            
            return JsonResponse({
                "message": f"Delivery partner {status} successfully",
                "partner": partner_data
            })
            
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)