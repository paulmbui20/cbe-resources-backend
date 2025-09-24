from django.db import models

from accounts.models import CustomUser
from core.models import TimestampedModel, UUIDModel
from orders.models import Order

User = CustomUser


class Payment(UUIDModel, TimestampedModel):
    """Payment record model"""
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    # External references
    external_reference = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)

    # Timestamps
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['transaction_id']),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.order.order_number}"


class MPesaPayment(UUIDModel, TimestampedModel):
    """M-Pesa specific payment model"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='mpesa_payment')

    # STK Push details
    checkout_request_id = models.CharField(max_length=100, blank=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)

    # Payment details
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account_reference = models.CharField(max_length=50)
    transaction_desc = models.CharField(max_length=100)

    # Response details
    mpesa_receipt_number = models.CharField(max_length=20, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)

    # Callback data
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True)

    def __str__(self):
        return f"M-Pesa Payment {self.phone_number} - {self.amount}"
