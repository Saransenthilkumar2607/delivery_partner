# Admin API Testing Guide

## Base URL
```
{{base_url}} = http://localhost:8000
```

## 1. Admin Authentication

### 1.1 Admin Login
**Endpoint:** `POST /api/admin/login/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
    "email": "admin@example.com",
    "password": "admin123"
}
```

**Expected Success Response (200):**
```json
{
    "message": "Admin login successful",
    "token": "uuid-token-here",
    "admin": {
        "id": 3,
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "ADMIN",
        "department": "Operations"
    }
}
```

**Error Responses:**
- 401: Invalid credentials
- 403: User is not an admin
- 500: Internal server error

---

### 1.2 Test Admin Login with Non-Admin User (Should Fail)
**Endpoint:** `POST /api/admin/login/`

**Request Body:**
```json
{
    "email": "john.doe@example.com",
    "password": "password123"
}
```

**Expected Error Response (403):**
```json
{
    "error": "Access denied. Admin role required."
}
```

---

## 2. Admin User Management

### 2.1 View All Users
**Endpoint:** `GET /api/admin/users/`

**Expected Success Response (200):**
```json
{
    "users": [
        {
            "id": 1,
            "email": "john.doe@example.com",
            "name": "John Doe",
            "role": "END_USER",
            "is_active": true,
            "phone_number": "+1234567890",
            "created_at": "2023-12-22T10:00:00Z",
            "address_line_1": "123 Main St",
            "address_line_2": "Apt 4B",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "USA",
            "delivery_notes": "Please call before delivery"
        },
        {
            "id": 2,
            "email": "partner@example.com",
            "name": "Mike Driver",
            "role": "DELIVERY_PARTNER",
            "is_active": true,
            "phone_number": "+1234567891",
            "created_at": "2023-12-22T10:00:00Z",
            "license_number": "DL123456789",
            "vehicle_type": "BIKE",
            "vehicle_number": "ABC-1234",
            "is_verified": true,
            "rating": 4.5,
            "total_deliveries": 25
        }
    ],
    "count": 2,
    "role_filter": null
}
```

---

### 2.2 View End Users Only
**Endpoint:** `GET /api/admin/users/?role=END_USER`

**Expected Success Response (200):**
```json
{
    "users": [
        {
            "id": 1,
            "email": "john.doe@example.com",
            "name": "John Doe",
            "role": "END_USER",
            "is_active": true,
            "phone_number": "+1234567890",
            "created_at": "2023-12-22T10:00:00Z",
            "address_line_1": "123 Main St",
            "address_line_2": "Apt 4B",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "USA",
            "delivery_notes": "Please call before delivery"
        }
    ],
    "count": 1,
    "role_filter": "END_USER"
}
```

---

### 2.3 View Delivery Partners Only
**Endpoint:** `GET /api/admin/users/?role=DELIVERY_PARTNER`

**Expected Success Response (200):**
```json
{
    "users": [
        {
            "id": 2,
            "email": "partner@example.com",
            "name": "Mike Driver",
            "role": "DELIVERY_PARTNER",
            "is_active": true,
            "phone_number": "+1234567891",
            "created_at": "2023-12-22T10:00:00Z",
            "license_number": "DL123456789",
            "vehicle_type": "BIKE",
            "vehicle_number": "ABC-1234",
            "is_verified": true,
            "rating": 4.5,
            "total_deliveries": 25
        }
    ],
    "count": 1,
    "role_filter": "DELIVERY_PARTNER"
}
```

---

## 3. Admin Delivery Management

### 3.1 View All Deliveries
**Endpoint:** `GET /api/admin/deliveries/`

**Expected Success Response (200):**
```json
{
    "deliveries": [
        {
            "id": 1,
            "tracking_number": "DEL12345678",
            "pickup_address": "123 Pickup Street, New York, NY 10001",
            "delivery_address": "456 Delivery Avenue, New York, NY 10002",
            "item_description": "Electronics - Laptop",
            "status": "ASSIGNED",
            "delivery_fee": 15.50,
            "pickup_notes": "Call before pickup",
            "delivery_notes": "Handle with care",
            "created_at": "2023-12-22T10:00:00Z",
            "pickup_time": "2023-12-22T10:30:00Z",
            "delivery_time": null,
            "end_user": {
                "id": 1,
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890"
            },
            "delivery_partner": {
                "id": 2,
                "name": "Mike Driver",
                "email": "partner@example.com",
                "phone_number": "+1234567891",
                "vehicle_type": "BIKE",
                "vehicle_number": "ABC-1234"
            }
        }
    ],
    "count": 1
}
```

---

### 3.2 Assign Delivery Partner to Delivery
**Endpoint:** `PUT /api/admin/deliveries/{delivery_id}/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
    "delivery_partner_id": 2
}
```

**Expected Success Response (200):**
```json
{
    "message": "Delivery partner assigned successfully",
    "delivery": {
        "id": 1,
        "tracking_number": "DEL12345678",
        "status": "ASSIGNED",
        "delivery_partner": {
            "id": 2,
            "name": "Mike Driver",
            "email": "partner@example.com",
            "vehicle_type": "BIKE",
            "vehicle_number": "ABC-1234"
        }
    }
}
```

**Error Responses:**
- 404: Delivery not found
- 404: Valid delivery partner not found
- 400: delivery_partner_id is required
- 500: Internal server error

---

## 4. Admin Delivery Partner Management

### 4.1 Get Available Delivery Partners
**Endpoint:** `GET /api/admin/delivery-partners/`

**Expected Success Response (200):**
```json
{
    "delivery_partners": [
        {
            "id": 2,
            "name": "Mike Driver",
            "email": "partner@example.com",
            "phone_number": "+1234567891",
            "vehicle_type": "BIKE",
            "vehicle_number": "ABC-1234",
            "rating": 4.5,
            "total_deliveries": 25,
            "license_number": "DL123456789",
            "is_active": true,
            "created_at": "2023-12-22T10:00:00Z"
        }
    ],
    "count": 1
}
```

---

## 5. Setup - Create Test Data

### 5.1 Create Admin User
**Endpoint:** `POST /api/users/user_list/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
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

---

### 5.2 Create End User
**Endpoint:** `POST /api/users/user_list/`

**Request Body:**
```json
{
    "email": "john.doe@example.com",
    "name": "John Doe",
    "password": "password123",
    "role": "END_USER",
    "phone_number": "+1234567890",
    "address_line_1": "123 Main St",
    "address_line_2": "Apt 4B",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA",
    "delivery_notes": "Please call before delivery"
}
```

---

### 5.3 Create Delivery Partner
**Endpoint:** `POST /api/users/user_list/`

**Request Body:**
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

---

### 5.4 Create Test Delivery
**Endpoint:** `POST /api/users/delivery/`

**Request Body:**
```json
{
    "end_user_id": 1,
    "pickup_address": "123 Pickup Street, New York, NY 10001",
    "delivery_address": "456 Delivery Avenue, New York, NY 10002",
    "item_description": "Electronics - Laptop",
    "delivery_fee": 15.50,
    "pickup_notes": "Call before pickup",
    "delivery_notes": "Handle with care"
}
```

---

## 6. Error Testing Scenarios

### 6.1 Test Invalid Credentials
**Endpoint:** `POST /api/admin/login/`

**Request Body:**
```json
{
    "email": "admin@example.com",
    "password": "wrongpassword"
}
```

**Expected Error Response (401):**
```json
{
    "error": "Invalid credentials"
}
```

---

### 6.2 Test Non-Existent Delivery Assignment
**Endpoint:** `PUT /api/admin/deliveries/9999/`

**Request Body:**
```json
{
    "delivery_partner_id": 2
}
```

**Expected Error Response (404):**
```json
{
    "error": "Delivery not found"
}
```

---

### 6.3 Test Invalid Delivery Partner Assignment
**Endpoint:** `PUT /api/admin/deliveries/1/`

**Request Body:**
```json
{
    "delivery_partner_id": 9999
}
```

**Expected Error Response (404):**
```json
{
    "error": "Valid delivery partner not found"
}
```

---

## 7. Summary of Admin API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/login/` | Admin login |
| GET | `/api/admin/users/` | View all users (optional `?role=` filter) |
| GET | `/api/admin/deliveries/` | View all deliveries |
| PUT | `/api/admin/deliveries/{id}/` | Assign delivery partner |
| GET | `/api/admin/delivery-partners/` | Get available delivery partners |

## 8. Testing Workflow

1. **Create test data** using the setup endpoints
2. **Login as admin** to get authentication token
3. **View users** to see all system users
4. **Filter users** by role to see specific user types
5. **View deliveries** to see all system deliveries
6. **Get available partners** to see who can be assigned
7. **Assign delivery partner** to a delivery
8. **Test error scenarios** to ensure proper validation

## 9. Important Notes

- All admin endpoints require the user to have `ADMIN` role
- Delivery partner assignment only works with verified and active partners
- The `end_user_id` in delivery creation must belong to a user with `END_USER` role
- Error responses include appropriate HTTP status codes and descriptive messages
- All timestamps are in ISO 8601 format (UTC)
