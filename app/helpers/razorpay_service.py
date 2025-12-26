import razorpay
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from app.helpers.base_model import BaseModel
from app.models.payment import Payment
from app.models.delivery import Delivery
from app.helpers.enums import PaymentStatus

logger = logging.getLogger(__name__)


class RazorpayService:
    """Razorpay payment service integration"""
    
    def __init__(self):
        # Initialize Razorpay client with environment variables
        key_id = os.getenv('RAZORPAY_KEY_ID')
        key_secret = os.getenv('RAZORPAY_KEY_SECRET')
        
        if not key_id or not key_secret:
            logger.error("Razorpay credentials not configured in environment variables")
            raise ValueError("Razorpay credentials not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        
        try:
            self.client = razorpay.Client(auth=(key_id, key_secret))
            logger.info("Razorpay client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Razorpay client: {str(e)}")
            raise Exception(f"Failed to initialize Razorpay client: {str(e)}")
    
    def create_order(self, amount: float, receipt: str = None, notes: Dict = None) -> Dict[str, Any]:
        """
        Create Razorpay order
        
        Args:
            amount: Amount in INR (will be converted to paise)
            receipt: Your order receipt ID
            notes: Additional notes for the order
        
        Returns:
            Razorpay order response
        """
        try:
            # Validate amount
            if not amount or amount <= 0:
                raise ValueError("Amount must be greater than 0")
            
            if amount > 100000:  # Maximum 1 lakh INR
                raise ValueError("Amount cannot exceed 100000 INR")
            
            # Convert INR to paise (multiply by 100)
            amount_paise = int(amount * 100)
            
            # Validate receipt
            if not receipt:
                receipt = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1,  # Auto-capture payment
                "notes": notes or {}
            }
            
            # Validate order data
            if not order_data["receipt"]:
                raise ValueError("Receipt ID is required")
            
            logger.info(f"Creating Razorpay order for amount: {amount} INR, receipt: {receipt}")
            order = self.client.order.create(data=order_data)
            logger.info(f"Razorpay order created successfully: {order['id']}")
            return order
            
        except ValueError as ve:
            logger.error(f"Validation error creating Razorpay order: {str(ve)}")
            raise ValueError(str(ve))
        except razorpay.errors.RazorpayError as re:
            logger.error(f"Razorpay API error creating order: {str(re)}")
            raise Exception(f"Razorpay API error: {str(re)}")
        except Exception as e:
            logger.error(f"Unexpected error creating Razorpay order: {str(e)}")
            raise Exception(f"Failed to create payment order: {str(e)}")
    
    def verify_payment(self, razorpay_order_id: str, razorpay_payment_id: str, 
                   razorpay_signature: str) -> bool:
        """
        Verify Razorpay payment signature
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Validate inputs
            if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                raise ValueError("All payment verification parameters are required")
            
            if len(razorpay_order_id) < 10 or len(razorpay_payment_id) < 10:
                raise ValueError("Invalid payment IDs format")
            
            if len(razorpay_signature) < 40:
                raise ValueError("Invalid signature format")
            
            # Create the signature string
            signature_string = f"{razorpay_order_id}|{razorpay_payment_id}"
            
            key_secret = os.getenv('RAZORPAY_KEY_SECRET')
            if not key_secret:
                raise ValueError("Razorpay secret key not configured")
            
            # Verify signature
            self.client.utility.verify_payment_signature(
                signature_string,
                razorpay_signature,
                key_secret
            )
            logger.info(f"Payment signature verified successfully for order: {razorpay_order_id}")
            return True
            
        except ValueError as ve:
            logger.error(f"Validation error verifying payment: {str(ve)}")
            raise ValueError(str(ve))
        except razorpay.errors.SignatureVerificationError:
            logger.error("Invalid Razorpay signature")
            return False
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise Exception(f"Payment verification failed: {str(e)}")
    
    def get_payment_details(self, razorpay_payment_id: str) -> Dict[str, Any]:
        """
        Get payment details from Razorpay
        
        Args:
            razorpay_payment_id: Payment ID from Razorpay
        
        Returns:
            Payment details from Razorpay
        """
        try:
            # Validate payment ID
            if not razorpay_payment_id:
                raise ValueError("Payment ID is required")
            
            if len(razorpay_payment_id) < 10:
                raise ValueError("Invalid payment ID format")
            
            logger.info(f"Fetching payment details for: {razorpay_payment_id}")
            payment = self.client.payment.fetch(razorpay_payment_id)
            logger.info(f"Payment details fetched successfully")
            return payment
            
        except ValueError as ve:
            logger.error(f"Validation error fetching payment details: {str(ve)}")
            raise ValueError(str(ve))
        except razorpay.errors.RazorpayError as re:
            logger.error(f"Razorpay API error fetching payment: {str(re)}")
            raise Exception(f"Payment not found: {str(re)}")
        except Exception as e:
            logger.error(f"Error fetching payment details: {str(e)}")
            raise Exception(f"Failed to fetch payment details: {str(e)}")
    
    def refund_payment(self, razorpay_payment_id: str, amount: float = None, 
                    reason: str = None) -> Dict[str, Any]:
        """
        Refund a payment
        
        Args:
            razorpay_payment_id: Payment ID to refund
            amount: Refund amount in INR (optional, full refund if not provided)
            reason: Reason for refund
        
        Returns:
            Refund details from Razorpay
        """
        try:
            # Validate payment ID
            if not razorpay_payment_id:
                raise ValueError("Payment ID is required")
            
            if len(razorpay_payment_id) < 10:
                raise ValueError("Invalid payment ID format")
            
            # Validate amount if provided
            if amount is not None:
                if amount <= 0:
                    raise ValueError("Refund amount must be greater than 0")
                if amount > 100000:
                    raise ValueError("Refund amount cannot exceed 100000 INR")
            
            # Validate reason
            if reason and len(reason) > 255:
                raise ValueError("Reason cannot exceed 255 characters")
            
            refund_data = {}
            if amount:
                refund_data["amount"] = int(amount * 100)  # Convert to paise
            if reason:
                refund_data["notes"] = {"reason": reason}
            
            logger.info(f"Processing refund for payment: {razorpay_payment_id}, amount: {amount}")
            refund = self.client.payment.refund(razorpay_payment_id, data=refund_data)
            logger.info(f"Refund processed successfully: {refund.get('id')}")
            return refund
            
        except ValueError as ve:
            logger.error(f"Validation error processing refund: {str(ve)}")
            raise ValueError(str(ve))
        except razorpay.errors.RazorpayError as re:
            logger.error(f"Razorpay API error processing refund: {str(re)}")
            raise Exception(f"Refund failed: {str(re)}")
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            raise Exception(f"Failed to process refund: {str(e)}")
    
    def capture_payment(self, razorpay_payment_id: str, amount: float) -> Dict[str, Any]:
        """
        Capture a payment (for payments that were authorized but not captured)
        
        Args:
            razorpay_payment_id: Payment ID to capture
            amount: Amount to capture in INR
        
        Returns:
            Capture details from Razorpay
        """
        try:
            # Validate inputs
            if not razorpay_payment_id:
                raise ValueError("Payment ID is required")
            
            if not amount or amount <= 0:
                raise ValueError("Amount must be greater than 0")
            
            if amount > 100000:
                raise ValueError("Amount cannot exceed 100000 INR")
            
            capture_data = {
                "amount": int(amount * 100),  # Convert to paise
                "currency": "INR"
            }
            
            logger.info(f"Capturing payment: {razorpay_payment_id}, amount: {amount}")
            capture = self.client.payment.capture(razorpay_payment_id, capture_data)
            logger.info(f"Payment captured successfully")
            return capture
            
        except ValueError as ve:
            logger.error(f"Validation error capturing payment: {str(ve)}")
            raise ValueError(str(ve))
        except razorpay.errors.RazorpayError as re:
            logger.error(f"Razorpay API error capturing payment: {str(re)}")
            raise Exception(f"Payment capture failed: {str(re)}")
        except Exception as e:
            logger.error(f"Error capturing payment: {str(e)}")
            raise Exception(f"Failed to capture payment: {str(e)}")


# Initialize Razorpay service instance
try:
    razorpay_service = RazorpayService()
    logger.info("Razorpay service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Razorpay service: {str(e)}")
    razorpay_service = None
