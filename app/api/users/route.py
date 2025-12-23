from django.urls import path
from app.api.users.controller import UserListController, UserDetailController, UserLoginController, DeliveryController

# User routes
urlpatterns = [
    # User CRUD operations
    path('user_list/', UserListController.as_view(), name='user_list_create'),
    path('<int:user_id>/', UserDetailController.as_view(), name='user_detail_update_delete'),
    
    # Authentication
    path('login/', UserLoginController.as_view(), name='user_login'),
    
    # Delivery management for end users
    path('delivery/', DeliveryController.as_view(), name='delivery_list_create'),
]
