import os

from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from core.models import TimestampedModel, UUIDModel


class CustomUser(AbstractUser):
    phone_number = PhoneNumberField(null=True, blank=True)
    is_vendor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', ]

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return full name or email if names not provided"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email.split('@')[0]

    def get_display_name(self):
        """Return display name for UI"""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Resize avatar if uploaded
        if self.avatar:
            self.resize_avatar()

    def resize_avatar(self):
        """Resize avatar to standard size"""
        if self.avatar and os.path.exists(self.avatar.path):
            with Image.open(self.avatar.path) as img:
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size, Image.Resampling.LANCZOS)
                    img.save(self.avatar.path, quality=85, optimize=True)


class DownloadLog(UUIDModel, TimestampedModel):
    """Track user download activity"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='download_logs')
    from orders.models import OrderItem
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='download_logs')
    ip_address = models.GenericIPAddressField()

    user_agent = models.TextField()# Browser info
    browser_family = models.CharField(max_length=100, default='Other')
    browser_version = models.CharField(max_length=50, default='Unknown')

    # OS info
    os_family = models.CharField(max_length=100, default='Other')
    os_version = models.CharField(max_length=50, default='Unknown')

    # Device info
    device_family = models.CharField(max_length=100, default='Other')
    device_brand = models.CharField(max_length=100, default='Unknown')
    device_model = models.CharField(max_length=100, default='Unknown')

    # Capabilities
    is_mobile = models.BooleanField(default=False)
    is_tablet = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)

    # Security
    is_suspicious = models.BooleanField(default=False)

    # Download details
    file_size = models.BigIntegerField(null=True, blank=True)
    download_duration = models.FloatField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    download_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('expired', 'Link Expired'),
            ('invalid', 'Invalid Token'),
            ('limit_exceeded', 'Download Limit Exceeded')
        ],
        default='success'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['order_item', 'created_at']),
            models.Index(fields=['download_status']),
        ]
        verbose_name = 'Download Log'
        verbose_name_plural = 'Download Logs'

    def __str__(self):
        return f"{self.user.email} - {self.order_item} - {self.created_at}"
