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
from app.helpers.enums import UserRole, DeliveryStatus, DeliveryPartnerStatus
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
# DELIVERY PARTNER LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerLoginController(View):

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

            if user.role != UserRole.DELIVERY_PARTNER:
                session.close()
                return JsonResponse({"error": "Access denied. Delivery partner role required."}, status=403)

            token = str(uuid.uuid4())
            session.close()

            return JsonResponse({
                "message": "Delivery partner login successful",
                "token": token,
                "delivery_partner": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "phone_number": user.phone_number,
                    "vehicle_type": user.vehicle_type,
                    "vehicle_number": user.vehicle_number,
                    "is_verified": user.is_verified,
                    "rating": user.rating,
                    "total_deliveries": user.total_deliveries
                }
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# DELIVERY PARTNER PROFILE
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerProfileController(View):
    """
    Delivery partner can view and update their profile
    """

    def get(self, request, partner_id):
        try:
            session = SessionLocal()
            
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            profile_data = {
                "id": partner.id,
                "email": partner.email,
                "name": partner.name,
                "role": partner.role,
                "is_active": partner.is_active,
                "phone_number": partner.phone_number,
                "license_number": partner.license_number,
                "vehicle_type": partner.vehicle_type,
                "vehicle_number": partner.vehicle_number,
                "is_verified": partner.is_verified,
                "rating": partner.rating,
                "total_deliveries": partner.total_deliveries,
                "created_at": partner.created_at.isoformat() if partner.created_at else None,
                "updated_at": partner.updated_at.isoformat() if partner.updated_at else None
            }
            
            session.close()
            return JsonResponse(profile_data)

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def put(self, request, partner_id):
        try:
            session = SessionLocal()
            
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            body = json.loads(request.body)

            # Update allowed fields
            updatable_fields = [
                "phone_number", "vehicle_type", "vehicle_number"
            ]
            
            for field in updatable_fields:
                if field in body:
                    setattr(partner, field, body[field])
            
            partner.updated_at = datetime.utcnow()
            session.commit()
            session.close()

            return JsonResponse({"message": "Profile updated successfully"})

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# DELIVERY PARTNER DELIVERIES
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerDeliveryController(View):
    """
    Delivery partner can view their assigned deliveries and update delivery status
    """

    def get(self, request, partner_id):
        try:
            session = SessionLocal()
            
            # Verify partner exists
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # Get deliveries assigned to this partner
            deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id
            ).all()

            data = []
            for d in deliveries:
                # Get end user details
                end_user = session.query(User).filter(User.id == d.end_user_id).first()

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
                        "phone_number": end_user.phone_number
                    } if end_user else None
                }
                data.append(delivery_data)
            
            session.close()

            return JsonResponse({
                "deliveries": data,
                "count": len(data),
                "partner_info": {
                    "id": partner.id,
                    "name": partner.name,
                    "rating": partner.rating,
                    "total_deliveries": partner.total_deliveries
                }
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def put(self, request, partner_id, delivery_id):
        """
        Update delivery status (PICKED_UP, DELIVERED, etc.)
        """
        try:
            body = json.loads(request.body)
            session = SessionLocal()

            # Verify partner exists
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # Get delivery assigned to this partner
            delivery = session.query(Delivery).filter(
                Delivery.id == delivery_id,
                Delivery.delivery_partner_id == partner_id
            ).first()
            
            if not delivery:
                session.close()
                return JsonResponse({"error": "Delivery not found or not assigned to you"}, status=404)

            new_status = body.get("status")
            if not new_status:
                session.close()
                return JsonResponse({"error": "status is required"}, status=400)

            # Validate status
            valid_statuses = [DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERED]
            if new_status not in valid_statuses:
                session.close()
                return JsonResponse({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}, status=400)

            # Update delivery status and timestamps
            old_status = delivery.status
            delivery.status = new_status
            delivery.updated_at = datetime.utcnow()

            if new_status == DeliveryStatus.PICKED_UP and old_status != DeliveryStatus.PICKED_UP:
                delivery.pickup_time = datetime.utcnow()
            elif new_status == DeliveryStatus.DELIVERED and old_status != DeliveryStatus.DELIVERED:
                delivery.delivery_time = datetime.utcnow()
                # Update partner's total deliveries
                partner.total_deliveries += 1

            session.commit()
            
            # Prepare delivery data before closing session
            delivery_data = {
                "id": delivery.id,
                "tracking_number": delivery.tracking_number,
                "status": delivery.status,
                "pickup_time": delivery.pickup_time.isoformat() if delivery.pickup_time else None,
                "delivery_time": delivery.delivery_time.isoformat() if delivery.delivery_time else None
            }
            
            session.close()

            return JsonResponse({
                "message": f"Delivery status updated to {new_status}",
                "delivery": delivery_data
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# DELIVERY PARTNER AVAILABILITY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerAvailabilityController(View):
    """
    Delivery partner can update their availability status
    """

    def put(self, request, partner_id):
        try:
            body = json.loads(request.body)
            session = SessionLocal()

            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # For now, we'll use is_active as availability status
            # In a real implementation, you might want to add a separate availability field
            is_available = body.get("is_available")
            if is_available is not None:
                partner.is_active = bool(is_available)
                partner.updated_at = datetime.utcnow()

            session.commit()
            session.close()

            return JsonResponse({
                "message": "Availability updated successfully",
                "is_available": partner.is_active
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)

    def get(self, request, partner_id):
        try:
            session = SessionLocal()

            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            session.close()

            return JsonResponse({
                "partner_id": partner.id,
                "name": partner.name,
                "is_available": partner.is_active,
                "is_verified": partner.is_verified,
                "current_deliveries": partner.total_deliveries,
                "rating": partner.rating
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)


# =====================================================
# DELIVERY PARTNER EARNINGS
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerEarningsController(View):
    """
    Delivery partner can view their earnings summary
    """

    def get(self, request, partner_id):
        try:
            session = SessionLocal()

            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()
            
            if not partner:
                session.close()
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # Get completed deliveries for this partner
            completed_deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id,
                Delivery.status == DeliveryStatus.DELIVERED
            ).all()

            total_earnings = sum(float(d.delivery_fee) if d.delivery_fee else 0 for d in completed_deliveries)
            total_tips = sum(float(d.tip) if d.tip else 0 for d in completed_deliveries)
            
            # This month's earnings
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_deliveries = [d for d in completed_deliveries if d.delivery_time and d.delivery_time >= current_month]
            this_month_earnings = sum(float(d.delivery_fee) if d.delivery_fee else 0 for d in this_month_deliveries)
            this_month_tips = sum(float(d.tip) if d.tip else 0 for d in this_month_deliveries)

            session.close()

            return JsonResponse({
                "partner_info": {
                    "id": partner.id,
                    "name": partner.name,
                    "rating": partner.rating,
                    "total_deliveries": partner.total_deliveries
                },
                "earnings": {
                    "total_earnings": total_earnings,
                    "total_tips": total_tips,
                    "total_income": total_earnings + total_tips,
                    "this_month_earnings": this_month_earnings,
                    "this_month_tips": this_month_tips,
                    "this_month_income": this_month_earnings + this_month_tips,
                    "completed_deliveries": len(completed_deliveries),
                    "this_month_deliveries": len(this_month_deliveries)
                }
            })

        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)