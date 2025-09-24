from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from accounts import views

urlpatterns = [

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Registration and Profile
    path('api/register/', views.UserRegistrationView.as_view(), name='register'),
    path('api/profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # Email verification
    path('api/resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend_verification'),

    # Availability checks
    path('api/check-username/', views.CheckUsernameAvailabilityView.as_view(), name='check_username'),
    path('api/check-email/', views.CheckEmailAvailabilityView.as_view(), name='check_email'),

    # Email verification endpoints
    path('api/send-verification/', views.SendVerificationEmailView.as_view(), name='send_verification'),
    path('api/verify-email/<str:uidb64>/<str:token>/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('api/resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend_verification'),
    path('api/verification-status/', views.CheckVerificationStatusView.as_view(), name='verification_status'),

]
