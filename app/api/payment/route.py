from django.urls import path
from app.api.payment.controller import (
    PaymentOrderController,
    PaymentVerificationController,
    PaymentHistoryController,
    PaymentRefundController
)

urlpatterns = [
    # Payment order creation
    path('create/', PaymentOrderController.as_view(), name='payment-order-create'),
    
    # Payment verification
    path('verify/', PaymentVerificationController.as_view(), name='payment-verify'),
    
    # Payment history
    path('history/<int:user_id>/', PaymentHistoryController.as_view(), name='payment-history'),
    
    # Payment refund
    path('refund/', PaymentRefundController.as_view(), name='payment-refund'),
]
