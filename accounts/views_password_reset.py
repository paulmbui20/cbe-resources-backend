import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import PasswordResetOTP
from accounts.serializers_password_reset import (
    PasswordResetRequestSerializer,
    PasswordResetVerifyOTPSerializer,
    PasswordResetConfirmSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    """
    API view for requesting a password reset via OTP.
    
    POST /accounts/api/password-reset/request/
    {
        "email": "user@example.com"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                
                # Get client info for security logging
                ip_address = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Generate OTP
                otp_obj = PasswordResetOTP.generate_otp(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # In a real application, send the OTP via email
                # For now, we'll just log it (in production, NEVER log OTPs)
                if settings.DEBUG:
                    logger.debug(f"OTP for {email}: {otp_obj.otp}")
                
                # Send OTP via email
                from accounts.tasks_password_reset import send_password_reset_otp
                send_password_reset_otp.delay(user.id, otp_obj.otp)
                
            except User.DoesNotExist:
                # For security reasons, don't reveal if email exists or not
                pass
            
            # Always return success to prevent email enumeration
            return Response({
                'success': True,
                'message': 'If your email is registered, you will receive a password reset OTP.'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordResetVerifyOTPView(APIView):
    """
    API view for verifying OTP code for password reset.
    
    POST /accounts/api/password-reset/verify-otp/
    {
        "email": "user@example.com",
        "otp": "123456"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetVerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            # OTP is valid, generate a temporary token for password reset
            user = serializer.validated_data['user']
            otp_obj = serializer.validated_data['otp_obj']
            
            # Create a short-lived token (10 minutes)
            refresh = RefreshToken.for_user(user)
            refresh.payload['reset_otp_id'] = str(otp_obj.id)
            refresh.payload['exp'] = datetime.timestamp(timezone.now() + timedelta(minutes=10))
            
            # Set token in HTTP-only cookie
            response = Response({
                'success': True,
                'message': 'OTP verified successfully. You can now reset your password.'
            }, status=status.HTTP_200_OK)
            
            # Set cookies
            self.set_token_cookies(response, str(refresh), str(refresh.access_token))
            
            return response
        
        return Response({
            'success': False,
            'message': 'OTP verification failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def set_token_cookies(self, response, refresh_token, access_token):
        """Set JWT tokens as HTTP-only cookies"""
        # Set refresh token cookie (longer expiry)
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=10 * 60,  # 10 minutes for password reset
            path='/accounts/api/token/refresh/'
        )
        
        # Set access token cookie (shorter expiry)
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=5 * 60,  # 5 minutes
            path='/'
        )


class PasswordResetConfirmView(APIView):
    """
    API view for setting a new password after OTP verification.
    
    POST /accounts/api/password-reset/confirm/
    {
        "email": "user@example.com",
        "otp": "123456",
        "new_password": "NewPassword123!",
        "confirm_password": "NewPassword123!"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            otp_obj = serializer.validated_data['otp_obj']
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            
            # Mark OTP as used
            otp_obj.use()
            
            # Generate new tokens
            refresh = RefreshToken.for_user(user)
            
            # Set token in HTTP-only cookie
            response = Response({
                'success': True,
                'message': 'Password has been reset successfully. You can now log in with your new password.'
            }, status=status.HTTP_200_OK)
            
            # Set cookies
            self.set_token_cookies(response, str(refresh), str(refresh.access_token))
            
            return response
        
        return Response({
            'success': False,
            'message': 'Password reset failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def set_token_cookies(self, response, refresh_token, access_token):
        """Set JWT tokens as HTTP-only cookies"""
        # Set refresh token cookie
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=24 * 60 * 60,  # 1 day
            path='/accounts/api/token/refresh/'
        )
        
        # Set access token cookie
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=5 * 60,  # 5 minutes
            path='/'
        )


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Takes a set of user credentials and returns JWT tokens as HTTP-only cookies
    """
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        
        # Get tokens
        refresh_token = serializer.validated_data['refresh']
        access_token = serializer.validated_data['access']
        
        # Create response
        response = Response({
            'success': True,
            'message': 'Login successful',
            'user': serializer.user.email  # Add basic user info
        }, status=status.HTTP_200_OK)
        
        # Set cookies
        self.set_token_cookies(response, refresh_token, access_token)
        
        return response
    
    def set_token_cookies(self, response, refresh_token, access_token):
        """Set JWT tokens as HTTP-only cookies"""
        # Set refresh token cookie
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=24 * 60 * 60,  # 1 day
            path='/accounts/api/token/refresh/'
        )
        
        # Set access token cookie
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=5 * 60,  # 5 minutes
            path='/'
        )


class CookieTokenRefreshView(TokenRefreshView):
    """
    Takes a refresh token from cookie and returns a new access token as HTTP-only cookie
    """
    
    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'success': False,
                'message': 'Refresh token not found in cookies'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Create serializer with token
        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({
                'success': False,
                'message': 'Invalid or expired refresh token',
                'detail': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get new access token
        access_token = serializer.validated_data['access']
        
        # Create response
        response = Response({
            'success': True,
            'message': 'Token refreshed successfully'
        }, status=status.HTTP_200_OK)
        
        # Set new access token cookie
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,  # Secure in production
            samesite='Lax',
            max_age=5 * 60,  # 5 minutes
            path='/'
        )
        
        return response


class CookieTokenLogoutView(APIView):
    """
    Logout view that clears JWT token cookies
    """
    
    def post(self, request):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            try:
                # Blacklist the token
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, AttributeError):
                # Token might be invalid or already blacklisted
                pass
        
        # Create response
        response = Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
        
        # Clear cookies
        response.delete_cookie('refresh_token', path='/accounts/api/token/refresh/')
        response.delete_cookie('access_token', path='/')
        
        return response