from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import CustomUser

@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    try:
        user = CustomUser.objects.get(id=user_id)

        subject = f'Welcome to {settings.SITE_NAME}!'
        html_message = render_to_string('emails/welcome.html', {
            'user': user,
            'site_name': settings.SITE_NAME,
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )

        return f"Welcome email sent to {user.email}"

    except CustomUser.DoesNotExist:
        return f"User with id {user_id} does not exist"
    except Exception as e:
        return f"Error sending welcome email: {str(e)}"

@shared_task
def send_credentials_email(user_id, password):
    """Send login credentials to user"""
    try:
        user = CustomUser.objects.get(id=user_id)

        subject = 'Your CBC Marketplace Login Details'
        html_message = render_to_string('emails/credentials.html', {
            'user': user,
            'password': password,
            'site_name': settings.SITE_NAME,
            'login_url': f"{settings.SITE_URL}/login/"
        })
        plain_message = strip_tags(html_message)


        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )

        return f"Credentials email sent to {user.email}"

    except CustomUser.DoesNotExist:
        return f"User with id {user_id} does not exist"
    except Exception as e:
        return f"Error sending credentials email: {str(e)}"


@shared_task
def send_verification_email(user_id, token, uid):
    """Send email verification link to user"""
    try:
        user = CustomUser.objects.get(id=user_id)

        # Build verification URL
        verification_url = f"{settings.SITE_URL}/accounts/api/verify-email/{uid}/{token}/"

        subject = f'Verify Your Email  - {settings.SITE_NAME}'

        html_message = render_to_string('emails/email_verification.html', {
            'user': user,
            'site_name': settings.SITE_NAME,
            'verification_url': verification_url,
            'expiry_hours': 24,  # Token expires in 24 hours
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )

        return f"Verification email sent to {user.email}"

    except CustomUser.DoesNotExist:
        return f"User with id {user_id} does not exist"
    except Exception as e:
        return f"Error sending verification email: {str(e)}"


@shared_task
def send_verification_success_email(user_id):
    """Send confirmation email after successful verification"""
    try:
        user = CustomUser.objects.get(id=user_id)

        subject = f'Email Verified Successfully - {settings.SITE_NAME}'
        html_message = render_to_string('emails/verification_success.html', {
            'user': user,
            'site_name': settings.SITE_NAME,
            'login_url': f"{settings.SITE_URL}/login/",
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )

        return f"Verification success email sent to {user.email}"

    except CustomUser.DoesNotExist:
        return f"User with id {user_id} does not exist"
    except Exception as e:
        return f"Error sending verification success email: {str(e)}"


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
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    import logging

    logger = logging.getLogger(__name__)

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
        text_content = render_to_string('emails/password_reset_otp.txt', context)

        # Create email
        subject = f"Password Reset Code for {settings.SITE_NAME}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        # Send email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,  # Plain text version as body
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")

        # Optional: Set email priority to high for security-related emails
        email.extra_headers = {
            'X-Priority': '2',
            'X-MSMail-Priority': 'High',
            'Importance': 'high'
        }

        email.send()

        logger.info(f"Password reset OTP sent to {user.email} (ID: {user.id})")
        return True

    except CustomUser.DoesNotExist:
        logger.error(f"Failed to send password reset OTP: User with ID {user_id} not found")
        return False
    except Exception as e:
        logger.error(f"Failed to send password reset OTP to user {user_id}: {str(e)}")
        return False

