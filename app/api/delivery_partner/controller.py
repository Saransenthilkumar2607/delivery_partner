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
from app.models.users import User

from app.helpers.enums import UserRole, DeliveryStatus, DeliveryPartnerStatus
from app.helpers.email_service import EmailService
from app.helpers.validators import (
    DeliveryPartnerValidator, 
    handle_validation_error, 
    validate_json_body,
    ValidationException
)
from app.helpers.database import get_database_session
from datetime import datetime

logger = logging.getLogger(__name__)


# =====================================================
# DELIVERY PARTNER LOGIN
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerLoginController(View):

    @handle_validation_error
    def post(self, request):
        body = validate_json_body(request)
        validated_data = DeliveryPartnerValidator.validate_login_data(body)

        session = get_database_session()
        try:
            user = session.query(User).filter(User.email == validated_data["email"]).first()
            if not user:
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            if not check_password(validated_data["password"], user.password_hash):
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            if not user.is_active:
                return JsonResponse({"error": "Account inactive"}, status=401)

            if user.role != "DELIVERY_PARTNER":
                return JsonResponse({"error": "Access denied. Delivery partner role required."}, status=403)

            return JsonResponse({
                "message": "Delivery partner login successful",
                "token": str(uuid.uuid4()),
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
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER PROFILE
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerProfileController(View):
    """
    Delivery partner can view and update their profile
    """

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
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
            
            return JsonResponse(profile_data)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)
        finally:
            session.close()

    @handle_validation_error
    def put(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)
            
            body = validate_json_body(request)
            validated_data = DeliveryPartnerValidator.validate_profile_update(body)

            # Update validated fields
            for field, value in validated_data.items():
                setattr(partner, field, value)
            
            session.commit()
            session.refresh(partner)

            return JsonResponse({"message": "Profile updated successfully"})
        except Exception as e:
            session.rollback()
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER DELIVERIES
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerDeliveryController(View):
    """
    Delivery partner can view their assigned deliveries and update delivery status
    """

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            # Verify partner exists
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)
            
            # Get deliveries assigned to this partner
            deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id
            ).all()

            data = []
            for delivery in deliveries:
                # Get end user manually
                end_user = session.query(User).filter(User.id == delivery.end_user_id).first() if delivery.end_user_id else None
                
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
                    "end_user": {
                        "id": end_user.id,
                        "name": end_user.name,
                        "phone_number": end_user.phone_number
                    } if end_user else None
                }
                data.append(delivery_data)

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
        finally:
            session.close()

    @handle_validation_error
    def put(self, request, partner_id, delivery_id):
        """
        Update delivery status (PICKED_UP, DELIVERED, etc.)
        """
        body = validate_json_body(request)
        validated_data = DeliveryPartnerValidator.validate_delivery_status_update(body)

        session = get_database_session()
        try:
            # Verify partner exists
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # Get delivery assigned to this partner
            delivery = session.query(Delivery).filter(
                Delivery.id == delivery_id,
                Delivery.delivery_partner_id == partner_id
            ).first()
            
            if not delivery:
                return JsonResponse({"error": "Delivery not found or not assigned to you"}, status=404)

            new_status = validated_data["status"]
            old_status = delivery.status

            # Update delivery status and timestamps
            delivery.status = new_status

            if new_status == "PICKED_UP" and old_status != "PICKED_UP":
                delivery.pickup_time = timezone.now()
            elif new_status == "DELIVERED" and old_status != "DELIVERED":
                delivery.delivery_time = timezone.now()
                # Update partner's total deliveries
                partner.total_deliveries += 1

            session.commit()
            session.refresh(delivery)
            session.refresh(partner)

            # Get end user for email
            end_user = session.query(User).filter(User.id == delivery.end_user_id).first()

            # Send email notification to end user for status update
            try:
                EmailService.send_delivery_status_update({
                    'tracking_number': delivery.tracking_number,
                    'pickup_address': delivery.pickup_address,
                    'delivery_address': delivery.delivery_address,
                    'item_description': delivery.item_description,
                    'updated_at': delivery.updated_at.isoformat() if delivery.updated_at else None,
                }, end_user.email if end_user else 'N/A', new_status)
            except Exception as e:
                logger.error(f"Failed to send delivery status email: {str(e)}")

            # If delivery is completed, send completion email
            if new_status == "DELIVERED":
                try:
                    EmailService.send_delivery_completed_to_user({
                        'tracking_number': delivery.tracking_number,
                        'delivery_address': delivery.delivery_address,
                        'item_description': delivery.item_description,
                        'delivered_at': delivery.delivery_time.isoformat() if delivery.delivery_time else None,
                        'customer_name': end_user.name if end_user else 'N/A',
                        'customer_email': end_user.email if end_user else 'N/A',
                        'partner_name': partner.name
                    })
                except Exception as e:
                    logger.error(f"Failed to send delivery completion email: {str(e)}")

            return JsonResponse({
                "message": "Delivery status updated successfully",
                "delivery": {
                    "id": delivery.id,
                    "tracking_number": delivery.tracking_number,
                    "status": delivery.status,
                    "pickup_time": delivery.pickup_time.isoformat() if delivery.pickup_time else None,
                    "delivery_time": delivery.delivery_time.isoformat() if delivery.delivery_time else None
                }
            })
        except Exception as e:
            session.rollback()
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER AVAILABILITY
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerAvailabilityController(View):
    """
    Delivery partner can update their availability status
    """

    @handle_validation_error
    def put(self, request, partner_id):
        session = get_database_session()
        try:
            body = validate_json_body(request)
            validated_data = DeliveryPartnerValidator.validate_availability_update(body)

            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # For now, we'll use is_active as availability status
            # In a real implementation, you might want to add a separate availability field
            partner.is_active = validated_data["is_available"]
            session.commit()
            session.refresh(partner)

            return JsonResponse({
                "message": "Availability updated successfully",
                "is_available": partner.is_active
            })
        except Exception as e:
            session.rollback()
            logger.exception(e)
            return JsonResponse({"error": "Internal server error"}, status=500)
        finally:
            session.close()

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

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
        finally:
            session.close()


# =====================================================
# DELIVERY PARTNER EARNINGS
# =====================================================

@method_decorator(csrf_exempt, name="dispatch")
class DeliveryPartnerEarningsController(View):
    """
    Delivery partner can view their earnings summary
    """

    def get(self, request, partner_id):
        session = get_database_session()
        try:
            partner = session.query(User).filter(
                User.id == partner_id,
                User.role == "DELIVERY_PARTNER"
            ).first()
            
            if not partner:
                return JsonResponse({"error": "Delivery partner not found"}, status=404)

            # Get completed deliveries for this partner
            completed_deliveries = session.query(Delivery).filter(
                Delivery.delivery_partner_id == partner_id,
                Delivery.status == "DELIVERED"
            ).all()

            total_earnings = sum(float(d.delivery_fee) if d.delivery_fee else 0 for d in completed_deliveries)
            total_tips = sum(float(d.tip) if d.tip else 0 for d in completed_deliveries)
            
            # This month's earnings
            current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_deliveries = [d for d in completed_deliveries if d.delivery_time and d.delivery_time >= current_month]
            this_month_earnings = sum(float(d.delivery_fee) if d.delivery_fee else 0 for d in this_month_deliveries)
            this_month_tips = sum(float(d.tip) if d.tip else 0 for d in this_month_deliveries)

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
        finally:
            session.close()
