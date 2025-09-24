from tinymce import models as tinymce_models
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class WebsiteInfo(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    logo = models.ImageField(upload_to="logo", null=True, blank=True)
    owner = models.CharField(max_length=100, null=True, blank=True)
    date_launched = models.DateField(null=True, blank=True)
    description =  tinymce_models.HTMLField(null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = PhoneNumberField(null=True, blank=True)

    def delete(self, *args, **kwargs):
        if self.logo:
            self.logo.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Website Info"
        verbose_name_plural = "Website Info"


class Contact(models.Model):
    priority_choices = [
        ('normal', 'normal'),
        ('urgent', 'urgent'),
    ]

    full_name = models.CharField(max_length=65)
    email = models.EmailField(max_length=65)
    phone = PhoneNumberField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=65, choices=priority_choices, default='normal')

    def __str__(self):
        return self.full_name


class TermsOfService(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, unique=True)
    description = tinymce_models.HTMLField()

    def __str__(self):
        return f"Terms of Service as at {self.last_update} - Active = {self.active}"


class PrivacyPolicy(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, unique=True)
    description =  tinymce_models.HTMLField()

    def __str__(self):
        return f"Privacy Policy as at {self.last_update} - Active = {self.active}"

    class Meta:
        verbose_name_plural = 'Privacy Policies'


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class Testimonials(models.Model):
    ROLE_CHOICES = (
        ('Principal', 'Principal'),
        ('Deputy-Principal', 'Deputy-Principal'),
        ('Headteacher', 'Headteacher'),
        ('Deputy-Headteacher', 'Deputy-Headteacher'),
        ('DOS', 'DOS'),
        ('Teacher', 'Teacher'),
        ('Student', 'Student'),
        ('Parent', 'Parent'),
    )
    date_added = models.DateTimeField(auto_now_add=True)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=65, choices=ROLE_CHOICES, default='Teacher')
    school_name = models.CharField(max_length=255, null=True, blank=True)
    school_location = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    rating = models.PositiveIntegerField()

    def __str__(self):
        return f"Testimonial of {self.full_name} on {self.date_added} on our service"

    class Meta:
        verbose_name_plural = 'Testimonials'
