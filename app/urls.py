from django.urls import path, include

urlpatterns = [
    path('api/users/', include('app.api.users.route')),
    path('api/admin/', include('app.api.admin.route')),
    path('api/delivery-partner/', include('app.api.delivery_partner.route')),
    path('api/payment/', include('app.api.payment.route')),
    path('api/', include('app.api.health.route')),
]

