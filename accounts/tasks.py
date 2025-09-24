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

        subject = 'Welcome to CBC Marketplace!'
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
            'login_url': f"{settings.SITE_URL}/accounts/login/"
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
        verification_url = f"{settings.SITE_URL}/api/accounts/verify-email/{uid}/{token}/"

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
            'login_url': f"{settings.SITE_URL}/accounts/login/",
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



