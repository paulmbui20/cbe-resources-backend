from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer, LogoutSerializer
)
from .tasks import send_welcome_email, send_verification_email, send_verification_success_email

User = CustomUser


class UserRegistrationView(APIView):
    """
    API view for user registration with minimal required fields.

    POST /accounts/api/register/
    {
        "email": "user@example.com",
        "username": "username",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()

                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)

                    # Generate verification token
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))

                    # Send welcome email asynchronously
                    send_welcome_email.delay(user.id)
                    send_verification_email.delay(user.id, token, uid)

                    # Prepare response data
                    user_data = UserProfileSerializer(user, context={'request': request}).data

                    return Response({
                        'success': True,
                        'message': 'Registration successful! Welcome email has been sent.',
                        'user': user_data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({
                    'success': False,
                    'message': 'Registration failed. Please try again.',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating user profile.

    GET /accounts/api/profile/
    PUT/PATCH /accounts/api/profile/
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': serializer.data
            })

        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    API view for changing user password.

    POST /accounts/api/change-password/
    {
        "old_password": "OldPassword123!",
        "new_password": "NewPassword123!",
        "new_password_confirm": "NewPassword123!"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Generate new tokens after password change
            refresh = RefreshToken.for_user(user)

            return Response({
                'success': True,
                'message': 'Password changed successfully',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })

        return Response({
            'success': False,
            'message': 'Password change failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CheckUsernameAvailabilityView(APIView):
    """
    API view to check if username is available.

    GET /accounts/api/check-username/?username=desired_username
    """
    permission_classes = [AllowAny]

    def get(self, request):
        username = request.query_params.get('username', '')

        if not username:
            return Response({
                'available': False,
                'message': 'Username is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(username) < 3:
            return Response({
                'available': False,
                'message': 'Username must be at least 3 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)

        available = not User.objects.filter(username=username).exists()

        return Response({
            'available': available,
            'message': 'Username is available' if available else 'Username is already taken'
        })


class CheckEmailAvailabilityView(APIView):
    """
    API view to check if email is available.

    GET /accounts/api/check-email/?email=user@example.com
    """
    permission_classes = [AllowAny]

    def get(self, request):
        email = request.query_params.get('email', '').lower()

        if not email:
            return Response({
                'available': False,
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        available = not User.objects.filter(email=email).exists()

        return Response({
            'available': available,
            'message': 'Email is available' if available else 'Email is already registered'
        })


class SendVerificationEmailView(APIView):
    """
    Send verification email to the current user
    POST /accounts/api/send-verification/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_verified:
            return Response({
                'success': False,
                'message': 'Your email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate verification token and uid
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        send_verification_email.delay(user.id, token, uid)

        return Response({
            'success': True,
            'message': f'Verification email sent to {user.email}. Please check your inbox.'
        }, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """
    Verify user's email with token from email link
    GET /accounts/api/verify-email/<uidb64>/<token>/
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            # Decode the user id
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            # Check if already verified
            if user.is_verified:
                return Response({
                    'success': False,
                    'message': 'Email is already verified.',
                    'redirect_url': f"{settings.SITE_URL}/login"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify the token
            if default_token_generator.check_token(user, token):
                # Mark user as verified
                user.is_verified = True
                user.save(update_fields=['is_verified'])

                # Send success email
                send_verification_success_email.delay(user.id)

                return Response({
                    'success': True,
                    'message': 'Email verified successfully! You can now access all features.',
                    'redirect_url': f"{settings.SITE_URL}/login"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Invalid or expired verification link.',
                    'redirect_url': f"{settings.SITE_URL}/resend-verification"
                }, status=status.HTTP_400_BAD_REQUEST)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'success': False,
                'message': 'Invalid verification link.',
                'redirect_url': f"{settings.SITE_URL}/resend-verification"
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    """
    Resend verification email with rate limiting
    POST /accounts/api/resend-verification/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_verified:
            return Response({
                'success': False,
                'message': 'Your email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check rate limiting (optional - you can store last sent time in cache/session)
        # This is a simple example - you might want to use Django's cache framework
        session_key = f'verification_sent_{user.id}'
        last_sent = request.session.get(session_key)
        from datetime import datetime, timedelta

        if last_sent:
            last_sent_time = datetime.fromisoformat(last_sent)
            if datetime.now() - last_sent_time < timedelta(minutes=5):
                return Response({
                    'success': False,
                    'message': 'Please wait 5 minutes before requesting another verification email.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Generate new token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Send email
        send_verification_email.delay(user.id, token, uid)

        # Update rate limiting
        request.session[session_key] = datetime.now().isoformat()

        return Response({
            'success': True,
            'message': f'Verification email resent to {user.email}. Please check your inbox.'
        }, status=status.HTTP_200_OK)


class CheckVerificationStatusView(APIView):
    """
    Check if current user's email is verified
    GET /accounts/api/verification-status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'is_verified': user.is_verified,
            'email': user.email,
            'message': 'Email is verified' if user.is_verified else 'Email is not verified'
        }, status=status.HTTP_200_OK)


class LogoutWithSerializerView(APIView):
    """
    Logout view using serializer for validation
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data['refresh_token']
                token = RefreshToken(refresh_token)
                token.blacklist()

                return Response(
                    {"message": "Successfully logged out"},
                    status=status.HTTP_200_OK
                )

            except TokenError:
                return Response(
                    {"error": "Invalid or expired token"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class LogoutAllView(APIView):
    """
    Logout from all devices by blacklisting all tokens for the user
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get all outstanding tokens for the user and blacklist them
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                try:
                    RefreshToken(token.token).blacklist()
                except TokenError:
                    # Token might already be blacklisted or expired
                    pass

            return Response(
                {"message": "Successfully logged out from all devices"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": "An error occurred during logout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
