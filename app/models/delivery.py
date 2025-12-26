from django.db import models
from app.helpers.enums import DeliveryStatus

class Delivery(models.Model):
    # Basic Information
    tracking_number = models.CharField(max_length=50, unique=True)
    end_user_id = models.IntegerField(blank=True, null=True)
    delivery_partner_id = models.IntegerField(blank=True, null=True)
    
    # Delivery Details
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    item_description = models.TextField()
    
    # Status and Tracking
    status = models.CharField(max_length=20, default=DeliveryStatus.PENDING)
    
    # Timing
    pickup_time = models.DateTimeField(blank=True, null=True)
    delivery_time = models.DateTimeField(blank=True, null=True)
    
    # Pricing
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional Notes
    pickup_notes = models.TextField(blank=True, null=True)
    delivery_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'deliveries'

    def __str__(self):
        return f"{self.tracking_number} - {self.status}"
        return f"Delivery {self.tracking_number} - {self.status}"