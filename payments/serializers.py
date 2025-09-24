from rest_framework import serializers

from orders.models import Order
from orders.serializers import OrderListSerializer
from payments.models import Payment, MPesaPayment


# Payment Serializers
class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    order = OrderListSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'currency', 'payment_method',
            'external_reference', 'transaction_id', 'status',
            'failure_reason', 'created_at', 'processed_at'
        ]


class MPesaPaymentSerializer(serializers.ModelSerializer):
    """M-Pesa payment serializer"""
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = MPesaPayment
        fields = [
            'id', 'payment', 'checkout_request_id', 'merchant_request_id',
            'phone_number', 'amount', 'account_reference', 'transaction_desc',
            'mpesa_receipt_number', 'transaction_date', 'result_code', 'result_desc'
        ]


class PaymentInitiateSerializer(serializers.Serializer):
    """Payment initiation serializer"""
    order_id = serializers.UUIDField()
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS)
    phone_number = serializers.CharField(max_length=15, required=False)

    def validate_phone_number(self, value):
        if self.validated_data.get('payment_method') == 'mpesa' and not value:
            raise serializers.ValidationError(
                "Phone number is required for M-Pesa payments"
            )

        if value:
            # Kenyan phone number validation
            import re
            phone_pattern = r'^(\+254|254|0)[17]\d{8}$'
            if not re.match(phone_pattern, value):
                raise serializers.ValidationError(
                    "Please enter a valid Kenyan phone number"
                )

        return value

    def validate_order_id(self, value):
        try:
            order = Order.objects.get(id=value, status='pending')
            return order
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or not pending")


class PaymentStatusSerializer(serializers.Serializer):
    """Payment status response serializer"""
    status = serializers.CharField()
    order_status = serializers.CharField()
    message = serializers.CharField()
    order_id = serializers.UUIDField(required=False)
    download_url = serializers.URLField(required=False)
