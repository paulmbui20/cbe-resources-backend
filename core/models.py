
from django.db import models
from django.utils import timezone
import uuid


class TimestampedModel(models.Model):
    """Abstract base model with created_at and updated_at fields"""
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base model with UUID primary key"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SEOModel(models.Model):
    """Abstract model for SEO fields"""
    meta_title = models.CharField(max_length=60, blank=True, help_text="SEO title (max 60 chars)")
    meta_description = models.CharField(max_length=160, blank=True, help_text="SEO description (max 160 chars)")
    meta_keywords = models.CharField(max_length=200, blank=True, help_text="SEO keywords, comma-separated")

    class Meta:
        abstract = True
