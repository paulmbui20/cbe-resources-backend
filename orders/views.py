import logging
from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.models import Payment, MPesaPayment
from payments.mpesa import MPesaAPI
from payments.serializers import PaymentInitiateSerializer
from products.models import Product
from .models import Order, OrderItem, Cart, CartItem
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    QuickCheckoutSerializer, CartSerializer, CartItemSerializer,
)

logger = logging.getLogger(__name__)


class OrderPagination(PageNumberPagination):
    """Custom pagination for orders"""
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 100


class OrderListAPIView(generics.ListAPIView):
    """
    List user's orders
    GET /api/orders
    """
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items__product'
        ).order_by('-created_at')


class OrderDetailAPIView(generics.RetrieveAPIView):
    """
    Get order details
    GET /api/orders/{order_id}
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items__product__vendor',
            'payments'
        )


class OrderCreateAPIView(generics.CreateAPIView):
    """
    Create a new order
    POST /api/orders
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_checkout(request):
    """
    Quick checkout for single product purchase
    POST /api/orders/quick-checkout
    """
    serializer = QuickCheckoutSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            product = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            # Create or get existing pending order
            order, created = Order.objects.get_or_create(
                user=request.user,
                status='pending',
                defaults={
                    'customer_email': serializer.validated_data['customer_email'],
                    'customer_phone': serializer.validated_data['customer_phone'],
                }
            )

            # Add product to order if not already added
            order_item, item_created = OrderItem.objects.get_or_create(
                order=order,
                product=product,
                defaults={
                    'unit_price': product.get_price(),
                    'quantity': quantity
                }
            )

            if not item_created:
                # Update quantity if item already exists
                order_item.quantity = quantity
                order_item.save()

            # Calculate totals
            order.calculate_totals()

            # Store order in session (for web compatibility)
            request.session['order_id'] = str(order.id)

            return Response({
                'success': True,
                'order': OrderDetailSerializer(order, context={'request': request}).data,
                'checkout_url': f'/api/orders/{order.id}/checkout'
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in quick checkout: {e}")
        return Response(
            {'error': 'Failed to create order'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkout_details(request, order_id):
    """
    Get checkout details for an order
    GET /api/orders/{order_id}/checkout
    """
    try:
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user,
            status='pending'
        )

        serializer = OrderDetailSerializer(order, context={'request': request})

        return Response({
            'order': serializer.data,
            'payment_methods': [
                {'value': 'mpesa', 'label': 'M-Pesa'},
                {'value': 'card', 'label': 'Credit/Debit Card'},
            ],
            'is_free': order.total_amount == 0
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_free_order(request, order_id):
    """
    Process free order (no payment required)
    POST /api/orders/{order_id}/process-free
    """
    try:
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user,
            status='pending'
        )

        # Verify order is actually free
        if order.total_amount > 0:
            return Response(
                {'error': 'This order requires payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark order as paid and process
        with transaction.atomic():
            order.status = 'paid'
            order.payment_method = 'free'
            order.payment_date = timezone.now()
            order.save()

            # Generate download links for all items
            for item in order.items.all():
                item.generate_download_link()

            # Update product download counts
            for item in order.items.all():
                item.product.increment_downloads()

        # Send confirmation email (background task)
        from .tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(order.id)

        # Clear session
        if 'order_id' in request.session:
            del request.session['order_id']

        return Response({
            'success': True,
            'message': 'Order processed successfully',
            'order': OrderDetailSerializer(order, context={'request': request}).data
        })

    except Exception as e:
        logger.error(f"Error processing free order {order_id}: {e}")
        return Response(
            {'error': 'Failed to process order'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """
    Initiate payment process
    POST /api/payments/initiate
    """
    serializer = PaymentInitiateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']
        phone_number = serializer.validated_data.get('phone_number')

        # Verify order belongs to user
        if order.user != request.user:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            amount=order.total_amount,
            payment_method=payment_method,
            status='pending'
        )

        if payment_method == 'mpesa':
            return handle_mpesa_payment(order, payment, phone_number)
        else:
            return Response(
                {'error': 'Payment method not supported'},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        return Response(
            {'error': 'Failed to initiate payment'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_mpesa_payment(order, payment, phone_number):
    """Handle M-Pesa payment initiation"""
    try:
        mpesa_api = MPesaAPI()

        # Create M-Pesa payment record
        mpesa_payment = MPesaPayment.objects.create(
            payment=payment,
            phone_number=phone_number,
            amount=order.total_amount,
            account_reference=f'ORDER_{order.order_number}',
            transaction_desc=f'CBC Materials - Order {order.order_number}'
        )

        # Initiate STK push
        response = mpesa_api.stk_push(
            phone_number=phone_number,
            amount=order.total_amount,
            account_reference=mpesa_payment.account_reference,
            transaction_desc=mpesa_payment.transaction_desc
        )

        # Update M-Pesa payment with response
        mpesa_payment.checkout_request_id = response.get('CheckoutRequestID', '')
        mpesa_payment.merchant_request_id = response.get('MerchantRequestID', '')
        mpesa_payment.save()

        # Update payment
        payment.external_reference = mpesa_payment.checkout_request_id
        payment.status = 'processing'
        payment.save()

        if response.get('ResponseCode') == '0':
            return Response({
                'success': True,
                'message': 'Payment request sent. Please check your phone and enter M-Pesa PIN.',
                'payment_id': str(payment.id),
                'checkout_request_id': mpesa_payment.checkout_request_id
            })
        else:
            payment.status = 'failed'
            payment.failure_reason = response.get('errorMessage', 'Unknown error')
            payment.save()

            return Response({
                'error': response.get('errorMessage', 'Payment failed')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error handling M-Pesa payment: {e}")
        payment.status = 'failed'
        payment.failure_reason = str(e)
        payment.save()

        return Response(
            {'error': 'Payment initiation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, payment_id):
    """
    Check payment status
    GET /api/payments/{payment_id}/status
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        # If payment is still processing, query M-Pesa API
        if payment.status == 'processing' and hasattr(payment, 'mpesa_payment'):
            try:
                mpesa_api = MPesaAPI()
                response = mpesa_api.query_payment_status(
                    payment.mpesa_payment.checkout_request_id
                )

                # Process response
                result_code = response.get('ResultCode')
                if result_code == '0':
                    payment.status = 'completed'
                    payment.processed_at = timezone.now()
                    payment.save()
                    payment.order.mark_as_paid()
                elif result_code in ['1032', '1037']:  # Cancelled or timeout
                    payment.status = 'cancelled'
                    payment.failure_reason = response.get('ResultDesc', 'Payment cancelled')
                    payment.save()

            except Exception as e:
                logger.error(f"Error querying payment status: {e}")

        # Prepare response
        response_data: dict[str, Any] = {
            'status': payment.status,
            'order_status': payment.order.status,
            'message': get_status_message(payment.status)
        }

        # Add order details if payment completed
        if payment.status == 'completed' and payment.order.status == 'paid':
            response_data['order_id'] = str(payment.order.id)
            response_data['download_items'] = [
                {
                    'product_title': item.product.title,
                    'download_url': item.get_download_url()
                }
                for item in payment.order.items.filter(download_token__isnull=False)
            ]

        return Response(response_data)

    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """
    Cancel pending order
    POST /api/orders/{order_id}/cancel
    """
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if not order.can_be_cancelled():
            return Response(
                {'error': 'Order cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'cancelled'
        order.save()

        return Response({
            'success': True,
            'message': f'Order {order.order_number} has been cancelled'
        })

    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return Response(
            {'error': 'Failed to cancel order'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Cart API Views
class CartAPIView(generics.RetrieveAPIView):
    """
    Get user's cart
    GET /api/cart
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    Add item to cart
    POST /api/cart/add
    """
    serializer = CartItemSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        # Get product
        product = get_object_or_404(Product, id=product_id, status='approved')

        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response({
            'success': True,
            'message': 'Item added to cart',
            'cart': CartSerializer(cart, context={'request': request}).data
        })

    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return Response(
            {'error': 'Failed to add item to cart'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    """
    Remove item from cart
    DELETE /api/cart/items/{item_id}
    """
    try:
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )
        cart_item.delete()

        return Response({
            'success': True,
            'message': 'Item removed from cart'
        })

    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        return Response(
            {'error': 'Failed to remove item from cart'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_status_message(status):
    """Get user-friendly status message"""
    messages = {
        'pending': 'Payment is being processed...',
        'processing': 'Please check your phone for M-Pesa prompt',
        'completed': 'Payment completed successfully!',
        'failed': 'Payment failed. Please try again.',
        'cancelled': 'Payment was cancelled.',
        'refunded': 'Payment has been refunded.'
    }
    return messages.get(status, 'Unknown status')