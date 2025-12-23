from django.urls import path
from app.api.admin.controller import AdminLoginController, AdminUserController, AdminDeliveryController, AdminDeliveryPartnerController

# Admin routes
urlpatterns = [
    # Admin Authentication
    path('login/', AdminLoginController.as_view(), name='admin_login'),
    
    # User Management - View end users and delivery partners
    path('users/', AdminUserController.as_view(), name='admin_users'),
    
    # Delivery Management - View all deliveries and assign partners
    path('deliveries/', AdminDeliveryController.as_view(), name='admin_deliveries'),
    path('deliveries/<int:delivery_id>/', AdminDeliveryController.as_view(), name='admin_delivery_assign'),
    
    # Delivery Partner Management - Get available partners for assignment
    path('delivery-partners/', AdminDeliveryPartnerController.as_view(), name='admin_delivery_partners'),
    path('delivery-partners/<int:partner_id>/', AdminDeliveryPartnerController.as_view(), name='admin_delivery_partner_verify'),
]