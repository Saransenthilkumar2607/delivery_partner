# Razorpay Payment Gateway Integration Guide

## Setup Instructions

### 1. Install Razorpay SDK
```bash
pip install razorpay
```

### 2. Environment Variables
Add these to your `.env` file:
```env
# Razorpay Test Credentials (replace with your actual keys)
RAZORPAY_KEY_ID=rzp_test_YourKeyID
RAZORPAY_KEY_SECRET=rzp_test_YourSecretKey

# Production Credentials (when ready)
# RAZORPAY_KEY_ID=rzp_live_YourKeyID
# RAZORPAY_KEY_SECRET=rzp_live_YourSecretKey
```

### 3. Update Razorpay Service
Modify `app/helpers/razorpay_service.py`:

```python
def __init__(self):
    # Load from environment variables
    key_id = os.getenv('RAZORPAY_KEY_ID')
    key_secret = os.getenv('RAZORPAY_KEY_SECRET')
    
    if not key_id or not key_secret:
        raise ValueError("Razorpay credentials not configured")
    
    self.client = razorpay.Client(auth=(key_id, key_secret))
```

## Database Tables Created

### Payments Table
- `order_id` - Your internal order ID
- `razorpay_order_id` - Razorpay order ID
- `razorpay_payment_id` - Razorpay payment ID
- `razorpay_signature` - Payment signature
- `amount` - Payment amount in INR
- `status` - Payment status (PENDING, COMPLETED, FAILED, REFUNDED)
- `user_id` - User who made payment
- `delivery_id` - Associated delivery
- `payment_completed_at` - Payment completion timestamp

### Payment Refunds Table
- `refund_id` - Internal refund ID
- `payment_id` - Reference to original payment
- `razorpay_refund_id` - Razorpay refund ID
- `amount` - Refund amount
- `reason` - Refund reason
- `status` - Refund status

## API Endpoints

### 1. Create Payment Order
```
POST /api/payment/create/
```

**Request Body:**
```json
{
    "user_id": 1,
    "delivery_id": 123,
    "amount": 150.50
}
```

**Response:**
```json
{
    "message": "Payment order created successfully",
    "payment": {
        "order_id": "ORDABC123DEF456",
        "razorpay_order_id": "order_1234567890",
        "amount": 150.50,
        "currency": "INR",
        "razorpay_key": "rzp_test_YourKeyID",
        "razorpay_order": {
            "id": "order_1234567890",
            "entity": "order",
            "amount": 15050,
            "currency": "INR",
            "status": "created"
        }
    }
}
```

### 2. Verify Payment
```
POST /api/payment/verify/
```

**Request Body:**
```json
{
    "order_id": "ORDABC123DEF456",
    "razorpay_payment_id": "pay_1234567890",
    "razorpay_signature": "abc123def456..."
}
```

**Response:**
```json
{
    "message": "Payment verified successfully",
    "payment": {
        "order_id": "ORDABC123DEF456",
        "status": "COMPLETED",
        "amount": 150.50,
        "payment_completed_at": "2023-12-23T10:30:00Z"
    }
}
```

### 3. Payment History
```
GET /api/payment/history/{user_id}/
```

**Response:**
```json
{
    "payments": [
        {
            "order_id": "ORDABC123DEF456",
            "amount": 150.50,
            "currency": "INR",
            "method": "RAZORPAY",
            "status": "COMPLETED",
            "created_at": "2023-12-23T10:25:00Z",
            "payment_completed_at": "2023-12-23T10:30:00Z",
            "delivery": {
                "id": 123,
                "tracking_number": "DEL12345678",
                "item_description": "Food delivery"
            }
        }
    ],
    "count": 1,
    "user": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
    }
}
```

### 4. Refund Payment (Admin)
```
POST /api/payment/refund/
```

**Request Body:**
```json
{
    "order_id": "ORDABC123DEF456",
    "reason": "Customer requested refund",
    "amount": 150.50,
    "processed_by": "Admin User"
}
```

## Frontend Integration

### 1. Include Razorpay Checkout Script
```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

### 2. Initialize Razorpay Payment
```javascript
// After getting order details from your API
function openRazorpayCheckout(orderDetails) {
    const options = {
        key: orderDetails.razorpay_key, // From API response
        amount: orderDetails.razorpay_order.amount, // Amount in paise
        currency: "INR",
        name: "Delivery Partner App",
        description: `Payment for delivery ${orderDetails.delivery?.tracking_number}`,
        order_id: orderDetails.razorpay_order_id, // From API response
        handler: function (response) {
            // Payment successful - send to verification endpoint
            verifyPayment(response);
        },
        prefill: {
            email: "user@example.com",
            contact: "9999999999"
        },
        theme: {
            color: "#3399cc"
        }
    };

    const rzp = new Razorpay(options);
    rzp.open();
}

// Verify payment with your backend
function verifyPayment(response) {
    fetch('/api/payment/verify/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            order_id: 'ORDABC123DEF456', // Your order ID
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            // Payment successful
            alert('Payment verified successfully!');
            // Redirect to success page
        } else {
            // Payment failed
            alert('Payment verification failed: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Payment verification error');
    });
}
```

### 3. Complete Payment Flow
```javascript
// 1. Create order
async function createPaymentOrder(deliveryId, amount) {
    const response = await fetch('/api/payment/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: getCurrentUserId(),
            delivery_id: deliveryId,
            amount: amount
        })
    });
    
    const orderDetails = await response.json();
    
    if (orderDetails.payment) {
        // 2. Open Razorpay checkout
        openRazorpayCheckout(orderDetails.payment);
    } else {
        alert('Error creating payment order: ' + orderDetails.error);
    }
}

// Usage example
createPaymentOrder(123, 150.50);
```

## Security Notes

1. **Always verify signatures** on your backend
2. **Never store secrets** in frontend code
3. **Use HTTPS** for all payment-related requests
4. **Validate amounts** before and after payment
5. **Log all transactions** for audit purposes

## Testing

1. Use Razorpay test credentials for development
2. Test with test card numbers provided by Razorpay
3. Verify webhook functionality
4. Test refund flow
5. Check error handling scenarios

## Production Deployment

1. Switch to live Razorpay credentials
2. Update webhook URLs to production endpoints
3. Enable 3D Secure authentication
4. Set up proper SSL certificates
5. Monitor payment success rates
