from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import PasswordResetOTP

User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate email exists in the system"""
        if not User.objects.filter(email=value.lower()).exists():
            # For security reasons, don't reveal if email exists or not
            # Just return the value and handle in the view
            pass
        return value.lower()


class PasswordResetVerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP code"""
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate(self, attrs):
        """Validate OTP is valid for the given email"""
        email = attrs.get('email').lower()
        otp = attrs.get('otp')

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "detail": "Invalid or expired OTP."
            })

        # Check if OTP exists and is valid
        try:
            otp_obj = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False
            ).latest('created_at')

            if not otp_obj.is_valid():
                raise serializers.ValidationError({
                    "detail": "Invalid or expired OTP."
                })

        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError({
                "detail": "Invalid or expired OTP."
            })

        # Store OTP object for later use in the view
        attrs['otp_obj'] = otp_obj
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for setting a new password after OTP verification"""
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate passwords match and OTP is valid"""
        # First validate that passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })

        # Then validate OTP using the OTP verification serializer
        otp_serializer = PasswordResetVerifyOTPSerializer(data={
            'email': attrs['email'],
            'otp': attrs['otp']
        })
        otp_serializer.is_valid(raise_exception=True)

        # Add validated data from OTP serializer
        attrs['user'] = otp_serializer.validated_data['user']
        attrs['otp_obj'] = otp_serializer.validated_data['otp_obj']

        return attrs