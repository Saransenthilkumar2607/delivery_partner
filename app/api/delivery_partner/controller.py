import json
import uuid
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from app.models.users import User
from app.models.delivery import Delivery

from app.helpers.enums import UserRole
from app.helpers.email_service import EmailService
from app.helpers.validators import (
    DeliveryPartnerValidator,
    validate_json_body,
)
from app.helpers.decorators import handle_validation_error
from app.helpers.database import get_database_session

logger = logging.getLogger(__name__)


# =====================================================
# DELIVERY PARTNER LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerLoginController(View):

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)
        validated = DeliveryPartnerValidator.validate_login_data(body)

        session = get_database_session()
        try:
            user = session.query(User).filter(
                User.email == validated["email"],
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not user or not check_password(validated["password"], user.password_hash):
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            if not user.is_active:
                return JsonResponse({"error": "Account inactive"}, status=403)

            return JsonResponse({
                "message": "Delivery partner login successful",
                "token": str(uuid.uuid4()),
                "delivery_partner": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "vehicle_type": user.vehicle_type,
                    "vehicle_number": user.vehicle_number,
                    "is_verified": user.is_verified,
                    "rating": user.rating,
                    "total_deliveries": user.total_deliveries or 0
                }
            })
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER PROFILE
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerProfileController(View):

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            return JsonResponse({
                "id": partner.id,
                "email": partner.email,
                "name": partner.name,
                "phone_number": partner.phone_number,
                "license_number": partner.license_number,
                "vehicle_type": partner.vehicle_type,
                "vehicle_number": partner.vehicle_number,
                "is_verified": partner.is_verified,
                "rating": partner.rating,
                "total_deliveries": partner.total_deliveries or 0,
                "created_at": partner.created_at.isoformat() if partner.created_at else None,
                "updated_at": partner.updated_at.isoformat() if partner.updated_at else None,
            })
        finally:
            session.close()

    @handle_validation_error
    def put(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            body = validate_json_body(request)
            validated = DeliveryPartnerValidator.validate_profile_update(body)

            for field, value in validated.items():
                setattr(partner, field, value)

            session.commit()
            return JsonResponse({"message": "Profile updated successfully"})
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER DELIVERIES
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerDeliveryController(View):

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id
            ).all()

            result = []
            for d in deliveries:
                result.append({
                    "id": d.id,
                    "tracking_number": d.tracking_number,
                    "pickup_address": d.pickup_address,
                    "delivery_address": d.delivery_address,
                    "item_description": d.item_description,
                    "status": d.status,
                    "delivery_fee": float(d.delivery_fee) if d.delivery_fee else None,
                    "pickup_time": d.pickup_time.isoformat() if d.pickup_time else None,
                    "delivery_time": d.delivery_time.isoformat() if d.delivery_time else None,
                })

            return JsonResponse({
                "count": len(result),
                "deliveries": result,
                "partner": {
                    "id": partner.id,
                    "name": partner.name,
                    "rating": partner.rating,
                    "total_deliveries": partner.total_deliveries or 0
                }
            })
        finally:
            session.close()

    @handle_validation_error
    def put(self, request, partner_id, delivery_id):
        """
        Update delivery status (PICKED_UP, DELIVERED)
        """
        body = validate_json_body(request)
        validated = DeliveryPartnerValidator.validate_delivery_status_update(body)

        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            delivery = session.query(Delivery).filter(
                Delivery.id == delivery_id,
                Delivery.delivery_partner_id == partner_id
            ).first()

            if not delivery:
                return JsonResponse(
                    {"error": "Delivery not found or not assigned to you"},
                    status=404
                )

            old_status = delivery.status
            new_status = validated["status"]

            delivery.status = new_status

            if new_status == "PICKED_UP" and old_status != "PICKED_UP":
                delivery.pickup_time = timezone.now()

            elif new_status == "DELIVERED" and old_status != "DELIVERED":
                delivery.delivery_time = timezone.now()
                partner.total_deliveries = (partner.total_deliveries or 0) + 1

            session.commit()

            return JsonResponse({
                "message": "Delivery status updated successfully",
                "delivery": {
                    "id": delivery.id,
                    "tracking_number": delivery.tracking_number,
                    "status": delivery.status,
                    "pickup_time": delivery.pickup_time.isoformat()
                    if delivery.pickup_time else None,
                    "delivery_time": delivery.delivery_time.isoformat()
                    if delivery.delivery_time else None,
                }
            })
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER AVAILABILITY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerAvailabilityController(View):

    @handle_validation_error
    def put(self, request, partner_id):
        body = validate_json_body(request)
        validated = DeliveryPartnerValidator.validate_availability_update(body)

        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            partner.is_active = validated["is_available"]
            session.commit()

            return JsonResponse({
                "message": "Availability updated",
                "is_available": partner.is_active
            })
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER EARNINGS
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerEarningsController(View):

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == UserRole.DELIVERY_PARTNER
            ).first()

            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id,
                Delivery.status == "DELIVERED"
            ).all()

            total_earnings = sum(float(d.delivery_fee or 0) for d in deliveries)
            total_tips = sum(float(d.tip or 0) for d in deliveries)

            return JsonResponse({
                "partner": {
                    "id": partner.id,
                    "name": partner.name,
                    "rating": partner.rating,
                    "total_deliveries": partner.total_deliveries or 0
                },
                "earnings": {
                    "total_earnings": total_earnings,
                    "total_tips": total_tips,
                    "total_income": total_earnings + total_tips,
                    "completed_deliveries": len(deliveries)
                }
            })
        finally:
            session.close()
