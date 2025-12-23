import re
import json
from typing import Dict, Any, List, Optional
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse

from app.helpers.enums import UserRole, DeliveryStatus, VehicleType


class ValidationException(Exception):
    """Custom exception for validation errors"""
    pass


class DeliveryPartnerValidator:
    """Validator for Delivery Partner operations"""
    
    @staticmethod
    def validate_login_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate login credentials"""
        errors = {}
        
        # Email validation
        email = data.get("email", "").strip()
        if not email:
            errors["email"] = "Email is required"
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Invalid email format"
        
        # Password validation
        password = data.get("password", "")
        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters long"
        
        if errors:
            raise ValidationException(errors)
        
        return {"email": email.lower(), "password": password}
    
    @staticmethod
    def validate_profile_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile update data"""
        errors = {}
        validated_data = {}
        
        # Phone number validation
        if "phone_number" in data:
            phone = data["phone_number"].strip()
            if phone:
                # Mobile number validation (exactly 10 digits)
                if not re.match(r'^[6-9]\d{9}$', phone):
                    errors["phone_number"] = "Invalid mobile number format (must be 10 digits starting with 6-9)"
                else:
                    validated_data["phone_number"] = phone
        
        # Vehicle type validation
        if "vehicle_type" in data:
            vehicle_type = data["vehicle_type"].strip().upper()
            valid_vehicles = [VehicleType.BIKE, VehicleType.CAR, VehicleType.VAN, VehicleType.TRUCK]
            if vehicle_type not in valid_vehicles:
                errors["vehicle_type"] = f"Invalid vehicle type. Must be one of: {', '.join(valid_vehicles)}"
            else:
                validated_data["vehicle_type"] = vehicle_type
        
        # Vehicle number validation
        if "vehicle_number" in data:
            vehicle_number = data["vehicle_number"].strip().upper()
            if vehicle_number:
                # Basic vehicle number format (e.g., "MH12AB1234" or "KA01CD5678")
                if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$', vehicle_number):
                    errors["vehicle_number"] = "Invalid vehicle number format (e.g., MH12AB1234)"
                else:
                    validated_data["vehicle_number"] = vehicle_number
        
        if errors:
            raise ValidationException(errors)
        
        return validated_data
    
    @staticmethod
    def validate_delivery_status_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate delivery status update"""
        errors = {}
        
        status = data.get("status", "").strip().upper()
        valid_statuses = [DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERED]
        
        if not status:
            errors["status"] = "Status is required"
        elif status not in valid_statuses:
            errors["status"] = f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        if errors:
            raise ValidationException(errors)
        
        return {"status": status}
    
    @staticmethod
    def validate_availability_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate availability update"""
        errors = {}
        
        is_available = data.get("is_available")
        if is_available is None:
            errors["is_available"] = "is_available field is required"
        elif not isinstance(is_available, bool):
            errors["is_available"] = "is_available must be a boolean value"
        
        if errors:
            raise ValidationException(errors)
        
        return {"is_available": is_available}


class DeliveryValidator:
    """Validator for Delivery operations"""
    
    @staticmethod
    def validate_delivery_creation(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate delivery creation data"""
        errors = {}
        validated_data = {}
        
        # End user ID validation
        if "end_user_id" not in data:
            errors["end_user_id"] = "End user ID is required"
        elif not isinstance(data["end_user_id"], int) or data["end_user_id"] <= 0:
            errors["end_user_id"] = "Invalid end user ID"
        else:
            validated_data["end_user_id"] = data["end_user_id"]
        
        # Pickup address validation
        pickup_address = data.get("pickup_address", "").strip()
        if not pickup_address:
            errors["pickup_address"] = "Pickup address is required"
        elif len(pickup_address) < 10:
            errors["pickup_address"] = "Pickup address must be at least 10 characters long"
        else:
            validated_data["pickup_address"] = pickup_address
        
        # Delivery address validation
        delivery_address = data.get("delivery_address", "").strip()
        if not delivery_address:
            errors["delivery_address"] = "Delivery address is required"
        elif len(delivery_address) < 10:
            errors["delivery_address"] = "Delivery address must be at least 10 characters long"
        else:
            validated_data["delivery_address"] = delivery_address
        
        # Item description validation
        item_description = data.get("item_description", "").strip()
        if not item_description:
            errors["item_description"] = "Item description is required"
        elif len(item_description) < 5:
            errors["item_description"] = "Item description must be at least 5 characters long"
        elif len(item_description) > 500:
            errors["item_description"] = "Item description must not exceed 500 characters"
        else:
            validated_data["item_description"] = item_description
        
        # Delivery fee validation
        if "delivery_fee" in data:
            delivery_fee = data["delivery_fee"]
            if delivery_fee is not None:
                try:
                    fee = float(delivery_fee)
                    if fee < 0:
                        errors["delivery_fee"] = "Delivery fee cannot be negative"
                    elif fee > 99999.99:
                        errors["delivery_fee"] = "Delivery fee is too high"
                    else:
                        validated_data["delivery_fee"] = fee
                except (ValueError, TypeError):
                    errors["delivery_fee"] = "Invalid delivery fee format"
        
        # Tip validation
        if "tip" in data:
            tip = data["tip"]
            if tip is not None:
                try:
                    tip_amount = float(tip)
                    if tip_amount < 0:
                        errors["tip"] = "Tip cannot be negative"
                    elif tip_amount > 1000:
                        errors["tip"] = "Tip amount cannot exceed 1000"
                    else:
                        validated_data["tip"] = tip_amount
                except (ValueError, TypeError):
                    errors["tip"] = "Invalid tip format"
        
        # Optional notes validation
        for field in ["pickup_notes", "delivery_notes"]:
            if field in data:
                notes = data[field]
                if notes is not None:
                    notes_str = str(notes).strip()
                    if len(notes_str) > 1000:
                        errors[field] = f"{field.replace('_', ' ').title()} must not exceed 1000 characters"
                    else:
                        validated_data[field] = notes_str if notes_str else None
        
        if errors:
            raise ValidationException(errors)
        
        return validated_data


class UserValidator:
    """Validator for User operations"""
    
    @staticmethod
    def validate_user_creation(data: Dict[str, Any], role: str = UserRole.END_USER) -> Dict[str, Any]:
        """Validate user creation data"""
        errors = {}
        validated_data = {}
        
        # Email validation
        email = data.get("email", "").strip()
        if not email:
            errors["email"] = "Email is required"
        else:
            try:
                validate_email(email)
                validated_data["email"] = email.lower()
            except ValidationError:
                errors["email"] = "Invalid email format"
        
        # Name validation
        name = data.get("name", "").strip()
        if not name:
            errors["name"] = "Name is required"
        elif len(name) < 2:
            errors["name"] = "Name must be at least 2 characters long"
        elif len(name) > 100:
            errors["name"] = "Name must not exceed 100 characters"
        else:
            validated_data["name"] = name
        
        # Password validation
        password = data.get("password", "")
        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters long"
        elif not re.search(r'[A-Z]', password):
            errors["password"] = "Password must contain at least one uppercase letter"
        elif not re.search(r'[a-z]', password):
            errors["password"] = "Password must contain at least one lowercase letter"
        elif not re.search(r'\d', password):
            errors["password"] = "Password must contain at least one digit"
        else:
            validated_data["password"] = password
        
        # Phone number validation
        phone = data.get("phone_number", "").strip()
        if phone:
            if not re.match(r'^[6-9]\d{9}$', phone):
                errors["phone_number"] = "Invalid mobile number format (must be 10 digits starting with 6-9)"
            else:
                validated_data["phone_number"] = phone
        
        # Role-specific validations
        if role == UserRole.DELIVERY_PARTNER:
            # License number validation
            license_number = data.get("license_number", "").strip()
            if not license_number:
                errors["license_number"] = "License number is required for delivery partners"
            elif len(license_number) < 5:
                errors["license_number"] = "License number must be at least 5 characters long"
            else:
                validated_data["license_number"] = license_number
            
            # Vehicle type validation
            vehicle_type = data.get("vehicle_type", "").strip().upper()
            if not vehicle_type:
                errors["vehicle_type"] = "Vehicle type is required for delivery partners"
            elif vehicle_type not in [VehicleType.BIKE, VehicleType.CAR, VehicleType.VAN, VehicleType.TRUCK]:
                errors["vehicle_type"] = f"Invalid vehicle type. Must be one of: BIKE, CAR, VAN, TRUCK"
            else:
                validated_data["vehicle_type"] = vehicle_type
            
            # Vehicle number validation
            vehicle_number = data.get("vehicle_number", "").strip().upper()
            if not vehicle_number:
                errors["vehicle_number"] = "Vehicle number is required for delivery partners"
            elif not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$', vehicle_number):
                errors["vehicle_number"] = "Invalid vehicle number format (e.g., MH12AB1234)"
            else:
                validated_data["vehicle_number"] = vehicle_number
        
        elif role == UserRole.END_USER:
            # Address validation for end users
            address_fields = ["address_line_1", "city", "state", "postal_code"]
            for field in address_fields:
                value = data.get(field, "").strip()
                if not value:
                    errors[field] = f"{field.replace('_', ' ').title()} is required for end users"
                else:
                    validated_data[field] = value
            
            # Postal code validation
            postal_code = data.get("postal_code", "").strip()
            if postal_code and not re.match(r'^\d{6}$', postal_code):
                errors["postal_code"] = "Invalid postal code format (must be 6 digits)"
        
        if errors:
            raise ValidationException(errors)
        
        validated_data["role"] = role
        return validated_data


def handle_validation_error(func):
    """Decorator to handle validation exceptions and return JSON responses"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationException as e:
            return JsonResponse({"errors": e.args[0]}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": "Internal server error"}, status=500)
    return wrapper


def validate_json_body(request):
    """Validate and parse JSON body from request"""
    try:
        if not request.body:
            raise ValidationException({"error": "Request body is required"})
        
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValidationException({"error": "Request body must be a JSON object"})
        
        return data
    except json.JSONDecodeError:
        raise ValidationException({"error": "Invalid JSON format"})
