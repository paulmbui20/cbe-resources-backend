import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task
def send_password_reset_otp(user_id, otp):
    """
    Send password reset OTP to user's email
    """
    from accounts.models import CustomUser
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Prepare email content
        context = {
            'user': user,
            'otp': otp,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
            'expiry_minutes': 30,  # OTP expires in 30 minutes
        }
        
        # Render email templates
        html_content = render_to_string('emails/password_reset.html', context)
        text_content = strip_tags(html_content)
        
        # Create email
        subject = f"Password Reset OTP for {settings.SITE_NAME}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email
        
        # Send email
        email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Password reset OTP sent to {user.email}")
        return True
        
    except CustomUser.DoesNotExist:
        logger.error(f"Failed to send password reset OTP: User with ID {user_id} not found")
        return False
    except Exception as e:
        logger.error(f"Failed to send password reset OTP: {str(e)}")
        return False