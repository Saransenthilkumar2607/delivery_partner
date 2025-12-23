from sqlalchemy import Column, String, Boolean, Text, Integer, Float, Enum, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.helpers.base_model import BaseModel
from app.helpers.enums import UserRole, VehicleType

class User(BaseModel):
    __tablename__ = "users"
    
    # Common fields
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default=UserRole.END_USER)
    phone_number = Column(String(20), nullable=True)
    
    # Address fields for delivery (for END_USER role)
    address_line_1 = Column(String(255), nullable=True)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="india")
    delivery_notes = Column(Text, nullable=True)
    
    # Delivery Partner specific fields
    license_number = Column(String(50), nullable=True)
    vehicle_type = Column(String(20), nullable=True)
    vehicle_number = Column(String(20), nullable=True)
    is_verified = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_deliveries = Column(Integer, default=0)
    
    # Admin specific fields
    department = Column(String(100), nullable=True)
    
    # Documents (stored in S3)
    license_document = Column(String(500), nullable=True)
    vehicle_document = Column(String(500), nullable=True)
    profile_photo = Column(String(500), nullable=True)
    
    def __repr__(self):
        return self.email