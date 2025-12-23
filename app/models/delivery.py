from sqlalchemy import Column, String, Text, Integer, Float, Enum, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.helpers.base_model import BaseModel
from app.helpers.enums import DeliveryStatus

class Delivery(BaseModel):
    __tablename__ = "deliveries"
    
    # Basic Information
    tracking_number = Column(String(50), unique=True, index=True, nullable=False)
    end_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_partner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Delivery Details
    pickup_address = Column(Text, nullable=False)
    delivery_address = Column(Text, nullable=False)
    item_description = Column(Text, nullable=False)
    
    # Status and Tracking
    status = Column(String(20), default=DeliveryStatus.PENDING)
    
    # Timing
    pickup_time = Column(DateTime(timezone=True), nullable=True)
    delivery_time = Column(DateTime(timezone=True), nullable=True)
    
    # Pricing
    delivery_fee = Column(Numeric(10, 2), nullable=True)
    tip = Column(Numeric(10, 2), default=0)
    
    # Notes
    pickup_notes = Column(Text, nullable=True)
    delivery_notes = Column(Text, nullable=True)
    
    # Relationships
    end_user = relationship("User", foreign_keys=[end_user_id], backref="user_deliveries")
    delivery_partner = relationship("User", foreign_keys=[delivery_partner_id], backref="partner_deliveries")
    
    def __repr__(self):
        return f"Delivery {self.tracking_number} - {self.status.value}"