from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem, Cart
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_order_confirmation_email(order_id):
    """Send order confirmation email with download links"""
    try:
        order = Order.objects.get(id=order_id)

        subject = f'Order Confirmation - {order.order_number}'
        html_message = render_to_string('emails/order_confirmation.html', {
            'order': order,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL
        })
        plain_message = strip_tags(html_message)

        recipient_email = order.customer_email or order.user.email

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Order confirmation email sent for order {order.order_number}")
        return f"Confirmation email sent for order {order.order_number}"

    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} does not exist")
        return f"Order with id {order_id} does not exist"
    except Exception as e:
        logger.error(f"Error sending confirmation email for order {order_id}: {e}")
        return f"Error sending confirmation email: {str(e)}"


@shared_task
def cleanup_expired_orders():
    """Clean up expired pending orders"""
    try:
        # Delete pending orders older than 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        expired_orders = Order.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        )

        count = expired_orders.count()
        expired_orders.delete()

        logger.info(f"Cleaned up {count} expired pending orders")
        return f"Cleaned up {count} expired pending orders"

    except Exception as e:
        logger.error(f"Error cleaning up expired orders: {e}")
        return f"Error cleaning up expired orders: {str(e)}"


@shared_task
def cleanup_expired_carts():
    """Clean up old shopping carts"""
    try:
        # Delete carts older than 7 days with no activity
        cutoff_time = timezone.now() - timedelta(days=7)
        old_carts = Cart.objects.filter(updated_at__lt=cutoff_time)

        count = old_carts.count()
        old_carts.delete()

        logger.info(f"Cleaned up {count} expired carts")
        return f"Cleaned up {count} expired carts"

    except Exception as e:
        logger.error(f"Error cleaning up expired carts: {e}")
        return f"Error cleaning up expired carts: {str(e)}"


@shared_task
def send_download_reminder_email(order_item_id):
    """Send reminder email before download link expires"""
    try:
        order_item = OrderItem.objects.get(id=order_item_id)
        order = order_item.order

        if order_item.can_download() and order_item.download_expires_at:
            days_left = (order_item.download_expires_at - timezone.now()).days

            if days_left <= 3:  # Send reminder when 3 days left
                subject = f'Download Reminder - {order_item.product.title}'
                html_message = render_to_string('emails/download_reminder.html', {
                    'order_item': order_item,
                    'order': order,
                    'days_left': days_left,
                    'site_name': 'CBC Marketplace',
                    'site_url': settings.SITE_URL
                })
                plain_message = strip_tags(html_message)

                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[order.user.email],
                    html_message=html_message,
                    fail_silently=False
                )

                logger.info(f"Download reminder sent for order item {order_item_id}")
                return f"Download reminder sent for order item {order_item_id}"

        return "No reminder needed"

    except OrderItem.DoesNotExist:
        logger.error(f"OrderItem with id {order_item_id} does not exist")
        return f"OrderItem with id {order_item_id} does not exist"
    except Exception as e:
        logger.error(f"Error sending download reminder for item {order_item_id}: {e}")
        return f"Error sending download reminder: {str(e)}"


# @shared_task
# def update_vendor_sales_stats():
#     """Update vendor sales statistics"""
#     try:
#         from vendors.models import VendorProfile
#         from django.db.models import Sum
#
#         vendors = VendorProfile.objects.all()
#
#         for vendor in vendors:
#             # Calculate total sales for this vendor
#             total_sales = OrderItem.objects.filter(
#                 product__vendor=vendor.user,
#                 order__status='paid'
#             ).aggregate(
#                 total=Sum('unit_price')
#             )['total'] or 0
#
#             vendor.total_sales = total_sales
#             vendor.save(update_fields=['total_sales'])
#
#         logger.info(f"Updated sales stats for {vendors.count()} vendors")
#         return f"Updated sales stats for {vendors.count()} vendors"
#
#     except Exception as e:
#         logger.error(f"Error updating vendor sales stats: {e}")
#         return f"Error updating vendor sales stats: {str(e)}"
