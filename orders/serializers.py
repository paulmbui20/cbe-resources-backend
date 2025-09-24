from django.contrib.auth import get_user_model
from rest_framework import serializers

from payments.models import Payment, MPesaPayment
from products.models import Product
from products.serializers import ProductListSerializer
from .models import Order, OrderItem, Cart, CartItem

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    can_download = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'unit_price', 'quantity',
            'total', 'download_token', 'download_count', 'download_limit',
            'download_expires_at', 'download_url', 'can_download'
        ]
        read_only_fields = ['download_token', 'download_count']

    def get_total(self, obj):
        return float(obj.get_total())

    def get_download_url(self, obj):
        return obj.get_download_url()

    def get_can_download(self, obj):
        return obj.can_download()


class OrderListSerializer(serializers.ModelSerializer):
    """Order list serializer (minimal fields)"""
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'total_amount',
            'total_items', 'payment_method', 'created_at'
        ]

    def get_total_items(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Order detail serializer (full fields)"""
    items = OrderItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    download_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'subtotal', 'tax_amount',
            'total_amount', 'payment_method', 'payment_reference',
            'payment_date', 'customer_email', 'customer_phone',
            'notes', 'items', 'total_items', 'can_be_cancelled',
            'download_items', 'created_at', 'updated_at'
        ]

    def get_total_items(self, obj):
        return obj.items.count()

    def get_can_be_cancelled(self, obj):
        return obj.can_be_cancelled()

    def get_download_items(self, obj):
        return OrderItemSerializer(
            obj.items.filter(download_token__isnull=False),
            many=True,
            context=self.context
        ).data


class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'customer_email', 'customer_phone', 'notes', 'items'
        ]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Order must have at least one item")

        # Validate products exist and are approved
        for item in items:
            try:
                product = Product.objects.get(
                    id=item['product_id'],
                    status='approved'
                )
                item['product'] = product
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Product with ID {item['product_id']} not found or not available"
                )

        return items

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        # Create order
        order = Order.objects.create(
            user=user,
            **validated_data
        )

        # Create order items
        for item_data in items_data:
            product = item_data.pop('product')
            OrderItem.objects.create(
                order=order,
                product=product,
                unit_price=product.get_price(),
                **item_data
            )

        # Calculate totals
        order.calculate_totals()

        return order


class QuickCheckoutSerializer(serializers.Serializer):
    """Quick checkout serializer for single product purchase"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=15)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, status='approved')
            return product
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or not available")

    def validate_customer_phone(self, value):
        # Add Kenyan phone number validation
        import re
        phone_pattern = r'^(\+254|254|0)[17]\d{8}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError(
                "Please enter a valid Kenyan phone number"
            )
        return value


class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total']

    def get_total(self, obj):
        return float(obj.get_total())

    def validate_product_id(self, value):
        try:
            Product.objects.get(id=value, status='approved')
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or not available")


class CartSerializer(serializers.ModelSerializer):
    """Cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'item_count', 'created_at']

    def get_total(self, obj):
        return float(obj.get_total())

    def get_item_count(self, obj):
        return obj.get_item_count()


class OrderSummarySerializer(serializers.Serializer):
    """Order summary for checkout"""
    items = OrderItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_free = serializers.SerializerMethodField()

    def get_is_free(self, obj):
        return obj.get('total_amount', 0) == 0


# Validation utilities
def validate_kenyan_phone(phone):
    """Validate Kenyan phone number"""
    import re
    # Remove spaces and special characters
    phone = re.sub(r'[^\d+]', '', phone)

    # Pattern for Kenyan mobile numbers
    patterns = [
        r'^\+254[17]\d{8}$',  # +254701234567
        r'^254[17]\d{8}$',  # 254701234567
        r'^0[17]\d{8}$',  # 0701234567
    ]

    for pattern in patterns:
        if re.match(pattern, phone):
            return True
    return False