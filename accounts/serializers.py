from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from orders.models import Order, OrderItem
from payments.models import Payment

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with only required fields"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password_confirm')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True}
        }

    def validate_email(self, value):
        """Validate email is unique and properly formatted"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        """Validate username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        """Create user with validated data"""
        validated_data.pop('password_confirm')

        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data['email'],
                username=validated_data['username'],
                password=validated_data['password']
            )
            return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (read and update)"""
    phone_number = PhoneNumberField(
        required=False,
        allow_blank=True,
        allow_null=True
    )
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'bio', 'avatar', 'avatar_url',
            'is_vendor', 'is_verified', 'email_notifications',
            'sms_notifications', 'full_name', 'display_name',
            'date_joined'
        )
        read_only_fields = (
            'id', 'email', 'username', 'is_vendor', 'is_verified', 'date_joined'
        )

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_display_name(self, obj):
        return obj.get_display_name()

    def validate_phone_number(self, value):
        """Normalize empty string to None"""
        return value or None

    def to_representation(self, instance):
        """Ensure phone_number returns null instead of empty string"""
        rep = super().to_representation(instance)
        if rep.get("phone_number") == "":
            rep["phone_number"] = None
        return rep


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

    def validate_old_password(self, value):
        """Validate old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserDownloadSerializer(serializers.ModelSerializer):
    """Serializer for user downloads"""
    product_name = serializers.SerializerMethodField()
    product_thumbnail = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            'id', 'product_name', 'product_thumbnail', 'download_url',
            'order_number', 'file_type', 'file_size', 'download_count',
            'download_expires_at', 'created_at'
        )

    def get_product_name(self, obj):
        """Get product name"""
        return obj.product.name if obj.product else 'Unknown Product'

    def get_product_thumbnail(self, obj):
        """Get product thumbnail URL"""
        if obj.product and obj.product.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.thumbnail.url)
            return obj.product.thumbnail.url
        return None

    def get_download_url(self, obj):
        """Get secure download URL"""
        if obj.download_token:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/downloads/{obj.download_token}/')
        return None

    def get_order_number(self, obj):
        """Get order number"""
        return obj.order.order_number if obj.order else None

    def get_file_type(self, obj):
        """Get file type"""
        if obj.product and obj.product.file:
            filename = obj.product.file.name
            return filename.split('.')[-1].upper() if '.' in filename else 'Unknown'
        return 'Unknown'

    def get_file_size(self, obj):
        """Get human-readable file size"""
        if obj.product and obj.product.file and hasattr(obj.product.file, 'size'):
            size_bytes = obj.product.file.size
            # Convert to human-readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0 or unit == 'GB':
                    break
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} {unit}"
        return 'Unknown'


class UserPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for user purchases (products purchased)"""
    product_name = serializers.SerializerMethodField()
    product_thumbnail = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    purchase_date = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    download_available = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            'id', 'product_name', 'product_thumbnail', 'product_type',
            'purchase_date', 'order_number', 'price', 'download_available',
            'download_url'
        )

    def get_product_name(self, obj):
        """Get product name"""
        return obj.product.name if obj.product else 'Unknown Product'

    def get_product_thumbnail(self, obj):
        """Get product thumbnail URL"""
        if obj.product and obj.product.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.thumbnail.url)
            return obj.product.thumbnail.url
        return None

    def get_product_type(self, obj):
        """Get product type"""
        return obj.product.get_product_type_display() if obj.product else 'Unknown'

    def get_purchase_date(self, obj):
        """Get purchase date"""
        return obj.order.payment_date if obj.order and obj.order.payment_date else obj.created_at

    def get_order_number(self, obj):
        """Get order number"""
        return obj.order.order_number if obj.order else None

    def get_price(self, obj):
        """Get price paid"""
        return obj.price

    def get_download_available(self, obj):
        """Check if download is available"""
        return bool(obj.download_token and obj.order and obj.order.status == 'paid')

    def get_download_url(self, obj):
        """Get secure download URL"""
        if obj.download_token and obj.order and obj.order.status == 'paid':
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/downloads/{obj.download_token}/')
        return None


class UserOrderSummarySerializer(serializers.ModelSerializer):
    """Serializer for user order summary"""
    item_count = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'created_at', 'status',
            'total_amount', 'payment_method', 'item_count',
            'payment_status'
        )

    def get_item_count(self, obj):
        """Get number of items in order"""
        return obj.items.count()

    def get_payment_status(self, obj):
        """Get payment status"""
        if obj.status == 'paid':
            return 'Completed'
        elif obj.status == 'pending':
            return 'Pending'
        elif obj.status == 'processing':
            return 'Processing'
        elif obj.status == 'failed':
            return 'Failed'
        elif obj.status == 'cancelled':
            return 'Cancelled'
        elif obj.status == 'refunded':
            return 'Refunded'
        return obj.status.capitalize()


class UserPaymentSerializer(serializers.ModelSerializer):
    """Serializer for user payment history"""
    order_number = serializers.SerializerMethodField()
    payment_method_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            'id', 'order_number', 'created_at', 'processed_at',
            'amount', 'currency', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'transaction_id'
        )

    def get_order_number(self, obj):
        """Get order number"""
        return obj.order.order_number if obj.order else None

    def get_payment_method_display(self, obj):
        """Get payment method display name"""
        return obj.get_payment_method_display()

    def get_status_display(self, obj):
        """Get status display name"""
        return obj.get_status_display()


class UserDashboardSerializer(serializers.ModelSerializer):
    """Serializer for user dashboard summary"""
    total_orders = serializers.SerializerMethodField()
    total_purchases = serializers.SerializerMethodField()
    total_downloads = serializers.SerializerMethodField()
    recent_orders = serializers.SerializerMethodField()
    recent_downloads = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'full_name', 'display_name',
            'total_orders', 'total_purchases', 'total_downloads',
            'recent_orders', 'recent_downloads'
        )

    def get_full_name(self, obj):
        """Get user's full name"""
        return obj.get_full_name()

    def get_display_name(self, obj):
        """Get user's display name"""
        return obj.get_display_name()

    def get_total_orders(self, obj):
        """Get total number of orders"""
        return obj.orders.count()

    def get_total_purchases(self, obj):
        """Get total number of purchases (order items)"""
        return OrderItem.objects.filter(order__user=obj).count()

    def get_total_downloads(self, obj):
        """Get total number of downloads"""
        from django.db.models import Sum
        result = OrderItem.objects.filter(
            order__user=obj,
            order__status='paid',
            download_token__isnull=False
        ).aggregate(total=Sum('download_count'))
        return result['total'] or 0

    def get_recent_orders(self, obj):
        """Get recent orders"""
        recent_orders = obj.orders.order_by('-created_at')[:5]
        return UserOrderSummarySerializer(recent_orders, many=True, context=self.context).data

    def get_recent_downloads(self, obj):
        """Get recent downloads"""
        recent_downloads = OrderItem.objects.filter(
            order__user=obj,
            order__status='paid',
            download_token__isnull=False
        ).order_by('-updated_at')[:5]
        return UserDownloadSerializer(recent_downloads, many=True, context=self.context).data


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout request validation
    """
    refresh_token = serializers.CharField(required=True)

    def validate_refresh_token(self, value):
        try:
            # Validate that the token is a valid refresh token
            RefreshToken(value)
            return value
        except TokenError:
            raise serializers.ValidationError("Invalid or expired refresh token")
