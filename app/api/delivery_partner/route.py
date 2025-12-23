from django.urls import path
from app.api.delivery_partner.controller import (
    DeliveryPartnerLoginController, 
    DeliveryPartnerProfileController, 
    DeliveryPartnerDeliveryController,
    DeliveryPartnerAvailabilityController,
    DeliveryPartnerEarningsController
)

# Delivery Partner routes
urlpatterns = [
    # Authentication
    path('login/', DeliveryPartnerLoginController.as_view(), name='delivery_partner_login'),
    
    # Profile Management
    path('profile/<int:partner_id>/', DeliveryPartnerProfileController.as_view(), name='delivery_partner_profile'),
    
    # Delivery Management
    path('deliveries/<int:partner_id>/', DeliveryPartnerDeliveryController.as_view(), name='delivery_partner_deliveries'),
    path('deliveries/<int:partner_id>/<int:delivery_id>/', DeliveryPartnerDeliveryController.as_view(), name='delivery_partner_update_delivery'),
    
    # Availability Management
    path('availability/<int:partner_id>/', DeliveryPartnerAvailabilityController.as_view(), name='delivery_partner_availability'),
    
    # Earnings
    path('earnings/<int:partner_id>/', DeliveryPartnerEarningsController.as_view(), name='delivery_partner_earnings'),
]