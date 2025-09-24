from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import WebsiteInfo, Contact, TermsOfService, PrivacyPolicy, FAQ, Testimonials


class WebsiteInfoSerializer(serializers.ModelSerializer):
    contact_phone = PhoneNumberField()

    class Meta:
        model = WebsiteInfo
        fields = [
            'id', 'name', 'url', 'logo', 'owner', 'date_launched',
            'description', 'contact_email', 'contact_phone'
        ]
        read_only_fields = ['id']


class ContactSerializer(serializers.ModelSerializer):
    phone = PhoneNumberField()

    class Meta:
        model = Contact
        fields = [
            'id', 'full_name', 'email', 'phone', 'message',
            'priority', 'is_read', 'submitted_at'
        ]
        read_only_fields = ['id', 'is_read', 'submitted_at']

    def validate_message(self, value):
        """Validate message length"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value


class ContactCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for contact form submission"""
    phone = PhoneNumberField()

    class Meta:
        model = Contact
        fields = ['full_name', 'email', 'phone', 'message', 'priority']

    def validate_message(self, value):
        """Validate message length"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value


class TermsOfServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfService
        fields = ['id', 'created_at', 'last_update', 'active', 'description']
        read_only_fields = ['id', 'created_at', 'last_update']


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ['id', 'created_at', 'last_update', 'active', 'description']
        read_only_fields = ['id', 'created_at', 'last_update']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonials
        fields = "__all__"
        read_only_fields = ["id", "date_added"]