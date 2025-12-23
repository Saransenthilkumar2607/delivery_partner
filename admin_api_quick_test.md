# Admin API Quick Testing Guide

## Base URL
```
{{base_url}} = http://localhost:8000
```

## 1. Admin Login
**POST** `/api/admin/login/`
```json
{
    "email": "admin@example.com",
    "password": "admin123"
}
```

## 2. View Users
**GET** `/api/admin/users/`
**GET** `/api/admin/users/?role=END_USER`
**GET** `/api/admin/users/?role=DELIVERY_PARTNER`

## 3. View All Deliveries
**GET** `/api/admin/deliveries/`

## 4. Assign Delivery Partner
**PUT** `/api/admin/deliveries/{delivery_id}/`
```json
{
    "delivery_partner_id": 2
}
```

## 5. Get Available Delivery Partners
**GET** `/api/admin/delivery-partners/`

## 6. Setup Test Data

### Create Admin
**POST** `/api/users/user_list/`
```json
{
    "email": "admin@example.com",
    "name": "Admin User",
    "password": "admin123",
    "role": "ADMIN",
    "phone_number": "+1234567892",
    "department": "Operations"
}
```

### Create End User
**POST** `/api/users/user_list/`
```json
{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "password123",
    "role": "END_USER",
    "phone_number": "+1234567890",
    "address_line_1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001"
}
```

### Create Delivery Partner
**POST** `/api/users/user_list/`
```json
{
    "email": "partner@example.com",
    "name": "Mike Driver",
    "password": "password123",
    "role": "DELIVERY_PARTNER",
    "phone_number": "+1234567891",
    "license_number": "DL123456789",
    "vehicle_type": "BIKE",
    "vehicle_number": "ABC-1234"
}
```

### Create Delivery
**POST** `/api/users/delivery/`
```json
{
    "end_user_id": 1,
    "pickup_address": "123 Pickup Street, NY 10001",
    "delivery_address": "456 Delivery Avenue, NY 10002",
    "item_description": "Electronics - Laptop",
    "delivery_fee": 15.50
}
```

## 7. Error Tests

### Invalid Admin Login
**POST** `/api/admin/login/`
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```
*Expected: 403 Error*

### Invalid Delivery Assignment
**PUT** `/api/admin/deliveries/9999/`
```json
{
    "delivery_partner_id": 2
}
```
*Expected: 404 Error*

## 8. Admin Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/admin/login/` | Admin authentication |
| GET | `/api/admin/users/` | View all users (filter by role) |
| GET | `/api/admin/deliveries/` | View all deliveries |
| PUT | `/api/admin/deliveries/{id}/` | Assign delivery partner |
| GET | `/api/admin/delivery-partners/` | Get available partners |

## 9. Testing Workflow

1. Create test data (admin, users, partners)
2. Login as admin
3. View users with role filters
4. View all deliveries
5. Get available partners
6. Assign partner to delivery
7. Test error scenarios

## 10. Key Features

- **Role-based access**: Only ADMIN role can access these endpoints
- **User filtering**: View users by role (END_USER, DELIVERY_PARTNER, ADMIN)
- **Delivery assignment**: Assign verified partners to deliveries
- **Comprehensive data**: Full user and delivery details
- **Error handling**: Proper HTTP status codes and messages
