from django.urls import path

from orders.views import initiate_payment, payment_status
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment endpoints
    path('payments/initiate/', initiate_payment, name='initiate-payment'),
    path('payments/<uuid:payment_id>/status/', payment_status, name='payment-status'),
    path('payments/<uuid:payment_id>/retry/', views.retry_payment, name='retry-payment'),
    path('payments/history/', views.payment_history, name='payment-history'),
    path('payments/methods/', views.payment_methods, name='payment-methods'),

    # M-Pesa callback (CSRF exempt)
    path('payments/mpesa/callback/', views.mpesa_callback, name='mpesa-callback'),

    # Generic webhook endpoint
    path('payments/webhook/<str:provider>/', views.generic_payment_webhook, name='payment-webhook'),
]
