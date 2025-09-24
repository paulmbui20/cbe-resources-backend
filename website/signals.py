from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from website.models import TermsOfService, PrivacyPolicy, WebsiteInfo, FAQ


@receiver(post_save, sender=TermsOfService)
def clear_tos_cache(sender, instance, **kwargs):
    if instance.active:
        # Generate both keys to delete
        cache_key = f'tos_content_{int(instance.last_update.timestamp())}'
        cache.delete_many(['active_tos', cache_key])


@receiver(post_save, sender=PrivacyPolicy)
def clear_privacy_cache(sender, instance, **kwargs):
    if instance.active:
        cache_key = f'privacy_content_{int(instance.last_update.timestamp())}'
        cache.delete_many(['active_privacy', cache_key])


@receiver(post_save, sender=WebsiteInfo)
def ensure_one_db_record(sender, instance, **kwargs):
    qs = sender.objects.all().count()
    if qs > 1:
        instance.delete()
        raise ValidationError({"error": "A website record already exists!"})


@receiver([post_save, post_delete], sender=WebsiteInfo)
def clear_website_info_cache(sender, instance, **kwargs):
    cache.delete('website_info')


@receiver([post_delete, post_save], sender=FAQ)
def clear_faq_cache(sender, instance, **kwargs):
    cache.delete('faqs_cache')
