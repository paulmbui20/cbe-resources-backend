from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from core.models import TimestampedModel, UUIDModel
from products.models import Product

User = CustomUser


class Order(UUIDModel, TimestampedModel):
    """Order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)

    # Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Payment information
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    # Customer information (for quick checkout)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        while True:
            number = ''.join(random.choices(string.digits, k=8))
            if not Order.objects.filter(order_number=number).exists():
                return number

    def calculate_totals(self):
        """Calculate order totals"""
        self.subtotal = sum(item.get_total() for item in self.items.all())
        self.tax_amount = 0  # No tax for now
        self.total_amount = self.subtotal + self.tax_amount
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

    def get_absolute_url(self):
        return reverse('orders:detail', kwargs={'pk': self.pk})

    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'processing']

    def mark_as_paid(self):
        """Mark order as paid and process"""
        self.status = 'paid'
        self.payment_date = timezone.now()
        self.save(update_fields=['status', 'payment_date'])

        # Generate download links for all items
        for item in self.items.all():
            item.generate_download_link()

        # Send notification email
        from .tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(self.id)


class OrderItem(UUIDModel, TimestampedModel):
    """Order item model"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # Price at time of purchase
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    # Download information
    download_token = models.CharField(max_length=100, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    download_limit = models.PositiveIntegerField(default=5)
    download_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.product.title} - Order {self.order.order_number}"

    def get_total(self):
        """Get total price for this item"""
        return self.unit_price * self.quantity

    def generate_download_link(self):
        """Generate secure download link"""
        from core.utils import generate_download_token

        self.download_token = generate_download_token(self.order.user.id, self.product.id)
        self.download_expires_at = timezone.now() + timedelta(days=30)  # 30 days access
        self.save(update_fields=['download_token', 'download_expires_at'])

    def get_download_url(self):
        """Get secure download URL"""
        if self.download_token:
            return reverse('orders:download', kwargs={'token': self.download_token})
        return None

    def can_download(self):
        """Check if item can still be downloaded"""
        if not self.download_token:
            return False
        if self.download_expires_at and timezone.now() > self.download_expires_at:
            return False
        if self.download_count >= self.download_limit:
            return False
        return True

    def increment_download(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])

        # Update product download count
        self.product.increment_downloads()


class Cart(UUIDModel, TimestampedModel):
    """Shopping cart for guest users"""
    session_key = models.CharField(max_length=40, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest cart {self.session_key}"

    def get_total(self):
        """Get cart total"""
        return sum(item.get_total() for item in self.items.all())

    def get_item_count(self):
        """Get total items in cart"""
        return self.items.count()

    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()


class CartItem(UUIDModel, TimestampedModel):
    """Cart item model"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.title} x{self.quantity}"

    def get_total(self):
        """Get total price for this item"""
        return self.product.get_price() * self.quantity
