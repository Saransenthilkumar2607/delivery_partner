# Email notification patch for delivery completion
# Add this code to the DeliveryPartnerDeliveryController.put method after session.commit()

# Send email notification to end user when delivery is completed
if new_status == DeliveryStatus.DELIVERED:
    end_user = session.query(User).filter(User.id == delivery.end_user_id).first()
    if end_user:
        delivery_details = {
            'tracking_number': delivery.tracking_number,
            'delivery_address': delivery.delivery_address,
            'item_description': delivery.item_description,
            'customer_name': end_user.name,
            'customer_email': end_user.email,
            'partner_name': partner.name,
            'delivered_at': delivery.delivery_time.isoformat() if delivery.delivery_time else None
        }
        EmailService.send_delivery_completed_to_user(delivery_details)
