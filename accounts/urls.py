from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from accounts import views
from accounts import views_dashboard
from accounts.views_password_reset import (
    PasswordResetRequestView,
    PasswordResetVerifyOTPView,
    PasswordResetConfirmView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CookieTokenLogoutView
)

urlpatterns = [
    path('api/csrf/', views.csrf_token_view, name='csrf'),

    # JWT Token endpoints with HTTP-only cookie support
    path('api/token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/token/logout/', CookieTokenLogoutView.as_view(), name='token_logout'),

    # Password Reset endpoints
    path('api/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/password-reset/verify-otp/', PasswordResetVerifyOTPView.as_view(), name='password_reset_verify_otp'),
    path('api/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

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

    # User Dashboard endpoints
    path('api/dashboard/', views_dashboard.UserDashboardView.as_view(), name='user_dashboard'),
    path('api/downloads/', views_dashboard.UserDownloadsView.as_view(), name='user_downloads'),
    path('api/purchases/', views_dashboard.UserPurchasesView.as_view(), name='user_purchases'),
    path('api/orders/', views_dashboard.UserOrdersView.as_view(), name='user_orders'),
    path('api/payments/', views_dashboard.UserPaymentsView.as_view(), name='user_payments'),
    path('api/stats/', views_dashboard.user_stats, name='user_stats'),
    path('api/download-history/', views_dashboard.download_history, name='download_history'),

    path('api/logout/', views.LogoutWithSerializerView.as_view(), name='logout_validated'),
    path('auth/logout-all/', views.LogoutAllView.as_view(), name='logout_all'),

]
