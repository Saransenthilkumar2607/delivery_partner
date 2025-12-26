from sqlalchemy import String
from sqlalchemy.dialects.mysql import ENUM

class UserRole:
    END_USER = "END_USER"
    ADMIN = "ADMIN"
    DELIVERY_PARTNER = "DELIVERY_PARTNER"

class DeliveryStatus:
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class DeliveryPartnerStatus:
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class VehicleType:
    BIKE = "BIKE"
    CAR = "CAR"
    VAN = "VAN"
    TRUCK = "TRUCK"

class PaymentStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

class PaymentMethod:
    RAZORPAY = "RAZORPAY"
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"
    UPI = "UPI"
