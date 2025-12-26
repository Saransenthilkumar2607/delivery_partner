from django.db import models
from app.helpers.enums import UserRole, VehicleType

class User(models.Model):
    # Common fields
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, default=UserRole.END_USER)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Address fields for delivery (for END_USER role)
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default="india")
    delivery_notes = models.TextField(blank=True, null=True)
    
    # Delivery partner specific fields
    license_number = models.CharField(max_length=50, blank=True, null=True)
    vehicle_type = models.CharField(max_length=20, blank=True, null=True)
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    rating = models.FloatField(default=0.0)
    total_deliveries = models.IntegerField(default=0)
    
    # Admin specific fields
    department = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.name} ({self.email})"
    
    # Documents (stored in S3)
    license_document = models.CharField(max_length=500, blank=True, null=True)
    vehicle_document = models.CharField(max_length=500, blank=True, null=True)
    profile_photo = models.CharField(max_length=500, blank=True, null=True)
    def __repr__(self):
        return self.email