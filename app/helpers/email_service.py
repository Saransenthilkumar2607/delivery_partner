import os
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class EmailService:
    
    @staticmethod
    def send_welcome_email_to_user(user_details):
        """
        Send welcome email to newly created user
        """
        logger.info(f"Email service received user_details: {user_details}")
        try:
            subject = f"Welcome to Delivery Partner System - {user_details.get('name', 'User')}"
            
            message = f"""
Dear {user_details.get('name', 'User')},

Welcome to the Delivery Partner System! Your account has been successfully created.

Account Details:
- Name: {user_details.get('name', 'N/A')}
- Email: {user_details.get('email', 'N/A')}
- Role: {user_details.get('role', 'N/A')}
- Created At: {user_details.get('created_at', 'N/A')}

You can now log in to your account and start using our services.

If you have any questions or need assistance, please contact our support team.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_email = user_details.get('email')
            
            # Skip sending email if email is empty, None, or just whitespace
            if not recipient_email or not recipient_email.strip():
                logger.warning(f"Cannot send welcome email: no valid email address provided for user {user_details.get('name', 'Unknown')}. Email value: '{recipient_email}'")
                return
            
            recipient_list = [recipient_email.strip()]
            
            logger.info(f"About to call send_mail. From: {from_email}, To: {recipient_list}, Subject: {subject}")
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Welcome email sent to user {user_details.get('email')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to user: {str(e)}")
            return False
    
    @staticmethod
    def send_partner_verification_email(partner_details):
        """
        Send email to delivery partner when verification status changes
        """
        try:
            status = "verified" if partner_details.get('is_verified') else "unverified"
            subject = f"Delivery Partner Account {status.title()} - {partner_details.get('name', 'Partner')}"
            
            message = f"""
Dear {partner_details.get('name', 'Delivery Partner')},

Your delivery partner account has been {status}.

Account Details:
- Name: {partner_details.get('name', 'N/A')}
- Email: {partner_details.get('email', 'N/A')}
- Status: {status.title()}
- Updated At: {partner_details.get('updated_at', 'N/A')}

{"You can now start accepting deliveries." if partner_details.get('is_verified') else "Please complete your verification process to start accepting deliveries."}

If you have any questions or need assistance, please contact our support team.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [partner_details.get('email')]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to partner {partner_details.get('email')} - status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to partner: {str(e)}")
            return False
    
    @staticmethod
    def send_order_created_to_admin(delivery_details):
        """
        Send email to admin when end user creates a new order
        """
        try:
            subject = f"New Delivery Order Created - #{delivery_details.get('tracking_number', 'N/A')}"
            
            message = f"""
Dear Admin,

A new delivery order has been created with the following details:

Order Details:
- Tracking Number: {delivery_details.get('tracking_number', 'N/A')}
- Pickup Address: {delivery_details.get('pickup_address', 'N/A')}
- Delivery Address: {delivery_details.get('delivery_address', 'N/A')}
- Item Description: {delivery_details.get('item_description', 'N/A')}
- Customer Name: {delivery_details.get('customer_name', 'N/A')}
- Customer Email: {delivery_details.get('customer_email', 'N/A')}
- Customer Phone: {delivery_details.get('customer_phone', 'N/A')}
- Created At: {delivery_details.get('created_at', 'N/A')}

Please review and assign a delivery partner.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [settings.ADMIN_EMAIL]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Order creation email sent to admin for order #{delivery_details.get('tracking_number')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send order creation email to admin: {str(e)}")
            return False
    
    @staticmethod
    def send_delivery_assigned_to_partner(delivery_details, partner_details):
        """
        Send email to delivery partner when admin assigns a delivery
        """
        try:
            subject = f"New Delivery Assignment - Order #{delivery_details.get('tracking_number', 'N/A')}"
            
            message = f"""
Dear {partner_details.get('name', 'Delivery Partner')},

You have been assigned a new delivery. Please find the details below:

Delivery Details:
- Tracking Number: {delivery_details.get('tracking_number', 'N/A')}
- Pickup Address: {delivery_details.get('pickup_address', 'N/A')}
- Delivery Address: {delivery_details.get('delivery_address', 'N/A')}
- Item Description: {delivery_details.get('item_description', 'N/A')}
- Customer Name: {delivery_details.get('customer_name', 'N/A')}
- Customer Phone: {delivery_details.get('customer_phone', 'N/A')}
- Delivery Fee: ${delivery_details.get('delivery_fee', 'N/A')}
- Assigned At: {delivery_details.get('assigned_at', 'N/A')}

Please pick up the package and deliver it as soon as possible.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [partner_details.get('email')]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Delivery assignment email sent to partner {partner_details.get('email')} for order #{delivery_details.get('tracking_number')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send delivery assignment email to partner: {str(e)}")
            return False
    
    @staticmethod
    def send_delivery_completed_to_user(delivery_details):
        """
        Send email to end user when delivery is completed
        """
        try:
            subject = f"Your Order Has Been Delivered - #{delivery_details.get('tracking_number', 'N/A')}"
            
            message = f"""
Dear {delivery_details.get('customer_name', 'Customer')},

Great news! Your order has been successfully delivered.

Delivery Details:
- Tracking Number: {delivery_details.get('tracking_number', 'N/A')}
- Delivered To: {delivery_details.get('delivery_address', 'N/A')}
- Item Description: {delivery_details.get('item_description', 'N/A')}
- Delivery Partner: {delivery_details.get('partner_name', 'N/A')}
- Delivered At: {delivery_details.get('delivered_at', 'N/A')}

Thank you for using our delivery service. If you have any questions or concerns, please contact our support team.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [delivery_details.get('customer_email')]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Delivery completion email sent to customer {delivery_details.get('customer_email')} for order #{delivery_details.get('tracking_number')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send delivery completion email to customer: {str(e)}")
            return False
    
    @staticmethod
    def send_delivery_status_update(delivery_details, recipient_email, status):
        """
        Send email notification for delivery status updates
        """
        try:
            subject = f"Delivery Status Update - Order #{delivery_details.get('tracking_number', 'N/A')}"
            
            message = f"""
Dear Customer,

Your delivery status has been updated.

Order Details:
- Tracking Number: {delivery_details.get('tracking_number', 'N/A')}
- Current Status: {status}
- Pickup Address: {delivery_details.get('pickup_address', 'N/A')}
- Delivery Address: {delivery_details.get('delivery_address', 'N/A')}
- Item Description: {delivery_details.get('item_description', 'N/A')}
- Updated At: {delivery_details.get('updated_at', 'N/A')}

You can track your order using the tracking number above.

Best regards,
Delivery Partner System
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [recipient_email]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Status update email sent to {recipient_email} for order #{delivery_details.get('tracking_number')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send status update email: {str(e)}")
            return False
