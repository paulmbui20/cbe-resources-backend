import os

from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    phone_number = PhoneNumberField(null=True, blank=True)
    is_vendor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username',]

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
