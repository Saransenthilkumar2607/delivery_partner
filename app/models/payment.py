from django.db import models
from app.helpers.enums import PaymentStatus, PaymentMethod


class Payment(models.Model):
    # Basic Information
    order_id = models.CharField(max_length=100, unique=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=500, blank=True, null=True)
    
    # Payment Details
    amount = models.FloatField()  # Amount in INR
    
    currency = models.CharField(max_length=3, default="INR")
    method = models.CharField(max_length=20, default=PaymentMethod.RAZORPAY)
    status = models.CharField(max_length=20, default=PaymentStatus.PENDING)
    
    # User Information
    user_id = models.IntegerField(blank=True, null=True)
    delivery_id = models.IntegerField(blank=True, null=True)
    
    # Payment Metadata
    notes = models.JSONField(blank=True, null=True)  # Store additional payment info
    error_description = models.TextField(blank=True, null=True)
    
    # Timestamps
    payment_completed_at = models.DateTimeField(blank=True, null=True)
    refund_initiated_at = models.DateTimeField(blank=True, null=True)
    refund_completed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment {self.order_id} - {self.status}"
    
    def __repr__(self):
        return f"Payment {self.order_id} - {self.status}"


class PaymentRefund(models.Model):
    # Basic Information
    refund_id = models.CharField(max_length=100, unique=True)
    payment_id = models.IntegerField(blank=True, null=True)
    razorpay_refund_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Refund Details
    amount = models.FloatField()  # Refund amount in INR
    reason = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default=PaymentStatus.PENDING)
    
    # Processing Information
    processed_by = models.CharField(max_length=100, blank=True, null=True)  # Admin who processed refund
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    refund_initiated_at = models.DateTimeField()
    refund_completed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_refunds'

    def __str__(self):
        return f"Refund {self.refund_id} - {self.status}"
