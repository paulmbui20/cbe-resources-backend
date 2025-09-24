import json
import logging
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Payment, MPesaPayment
from .mpesa import MPesaAPI
from orders.models import Order

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """
    M-Pesa payment callback
    POST /api/payments/mpesa/callback
    """
    try:
        callback_data = json.loads(request.body)
        logger.info(f"M-Pesa callback received: {callback_data}")

        # Extract callback data
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        if not checkout_request_id:
            logger.error("No CheckoutRequestID in callback")
            return HttpResponse('OK')

        # Find M-Pesa payment
        try:
            mpesa_payment = MPesaPayment.objects.get(
                checkout_request_id=checkout_request_id
            )
        except MPesaPayment.DoesNotExist:
            logger.error(
                f"M-Pesa payment not found for CheckoutRequestID: {checkout_request_id}"
            )
            return HttpResponse('OK')

        # Update M-Pesa payment
        mpesa_payment.result_code = result_code
        mpesa_payment.result_desc = result_desc

        if result_code == 0:  # Success
            # Extract payment details
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')

                if name == 'MpesaReceiptNumber':
                    mpesa_payment.mpesa_receipt_number = value
                elif name == 'TransactionDate':
                    # Convert timestamp to datetime
                    try:
                        timestamp = str(value)
                        mpesa_payment.transaction_date = datetime.strptime(
                            timestamp, '%Y%m%d%H%M%S'
                        )
                        # Make it timezone-aware
                        mpesa_payment.transaction_date = timezone.make_aware(
                            mpesa_payment.transaction_date, timezone.get_current_timezone()
                        )
                    except Exception:
                        mpesa_payment.transaction_date = timezone.now()

            # Update payment and order
            payment = mpesa_payment.payment
            payment.status = 'completed'
            payment.transaction_id = mpesa_payment.mpesa_receipt_number
            payment.processed_at = timezone.now()
            payment.save()

            # Mark order as paid
            order = payment.order
            order.mark_as_paid()

            logger.info(f"Payment successful for order {order.order_number}")

        else:  # Failed
            payment = mpesa_payment.payment
            payment.status = 'failed'
            payment.failure_reason = result_desc
            payment.save()

            logger.warning(
                f"Payment failed for order {payment.order.order_number}: {result_desc}"
            )

        mpesa_payment.save()
        return HttpResponse('OK')

    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {e}")
        return HttpResponse('ERROR')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_payment(request, payment_id):
    """
    Retry a failed payment
    POST /api/payments/{payment_id}/retry
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        if payment.status not in ['failed', 'cancelled']:
            return Response(
                {'error': 'Payment cannot be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset payment status
        payment.status = 'pending'
        payment.failure_reason = ''
        payment.save()

        # If M-Pesa payment, initiate new STK push
        if payment.payment_method == 'mpesa' and hasattr(payment, 'mpesa_payment'):
            mpesa_payment = payment.mpesa_payment
            mpesa_api = MPesaAPI()

            response = mpesa_api.stk_push(
                phone_number=mpesa_payment.phone_number,
                amount=mpesa_payment.amount,
                account_reference=mpesa_payment.account_reference,
                transaction_desc=mpesa_payment.transaction_desc
            )

            # Update M-Pesa payment with new response
            mpesa_payment.checkout_request_id = response.get('CheckoutRequestID', '')
            mpesa_payment.merchant_request_id = response.get('MerchantRequestID', '')
            mpesa_payment.result_code = None
            mpesa_payment.result_desc = ''
            mpesa_payment.save()

            # Update payment
            payment.external_reference = mpesa_payment.checkout_request_id
            payment.status = 'processing'
            payment.save()

            if response.get('ResponseCode') == '0':
                return Response({
                    'success': True,
                    'message': 'Payment retry initiated. Please check your phone.',
                    'payment_id': str(payment.id)
                })
            else:
                payment.status = 'failed'
                payment.failure_reason = response.get('errorMessage', 'Unknown error')
                payment.save()

                return Response({
                    'error': response.get('errorMessage', 'Payment retry failed')
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': 'Payment reset successfully'
        })

    except Exception as e:
        logger.error(f"Error retrying payment {payment_id}: {e}")
        return Response(
            {'error': 'Failed to retry payment'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """
    Get user's payment history
    GET /api/payments/history
    """
    try:
        payments = Payment.objects.filter(
            user=request.user
        ).select_related(
            'order'
        ).order_by('-created_at')

        # Simple pagination
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 20))
        start = (page - 1) * page_size
        end = start + page_size

        payments_page = payments[start:end]

        payments_data = []
        for payment in payments_page:
            payments_data.append({
                'id': str(payment.id),
                'order_number': payment.order.order_number,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'payment_method': payment.payment_method,
                'status': payment.status,
                'created_at': payment.created_at.isoformat(),
                'processed_at': payment.processed_at.isoformat() if payment.processed_at else None
            })

        return Response({
            'payments': payments_data,
            'total': payments.count(),
            'page': page,
            'pageSize': len(payments_data),
            'hasMore': end < payments.count()
        })

    except Exception as e:
        logger.error(f"Error fetching payment history: {e}")
        return Response(
            {'error': 'Failed to fetch payment history'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def payment_methods(request):
    """
    Get available payment methods
    GET /api/payments/methods
    """
    methods = [
        {
            'value': 'mpesa',
            'label': 'M-Pesa',
            'description': 'Pay using your M-Pesa mobile money account',
            'icon': 'mpesa-icon',
            'requires_phone': True
        },
        {
            'value': 'card',
            'label': 'Credit/Debit Card',
            'description': 'Pay using Visa, MasterCard, or local cards',
            'icon': 'card-icon',
            'requires_phone': False,
            'disabled': True  # Not implemented yet
        }
    ]

    return Response({'payment_methods': methods})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_refund(request, order_id):
    """
    Request refund for an order
    POST /api/orders/{order_id}/refund
    """
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status != 'paid':
            return Response(
                {'error': 'Only paid orders can be refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if refund is still allowed (within 24 hours)
        time_limit = timezone.now() - timedelta(hours=24)
        if order.payment_date and order.payment_date < time_limit:
            return Response(
                {'error': 'Refund period has expired (24 hours)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Refund reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create refund request (you might want to create a RefundRequest model)
        # For now, we'll just update the order notes
        order.notes = f"REFUND REQUESTED: {reason}\nRequested at: {timezone.now()}"
        order.save()

        # Notify admin about refund request (implement as needed)
        logger.info(f"Refund requested for order {order.order_number}: {reason}")

        return Response({
            'success': True,
            'message': 'Refund request submitted successfully. We will process it within 24 hours.'
        })

    except Exception as e:
        logger.error(f"Error requesting refund for order {order_id}: {e}")
        return Response(
            {'error': 'Failed to submit refund request'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_invoice(request, order_id):
    """
    Get order invoice/receipt
    GET /api/orders/{order_id}/invoice
    """
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status != 'paid':
            return Response(
                {'error': 'Invoice only available for paid orders'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get payment information
        payment = order.payments.filter(status='completed').first()

        invoice_data = {
            'order': {
                'id': str(order.id),
                'order_number': order.order_number,
                'date': order.created_at.isoformat(),
                'payment_date': order.payment_date.isoformat() if order.payment_date else None,
                'status': order.status
            },
            'customer': {
                'email': order.customer_email,
                'phone': order.customer_phone
            },
            'items': [],
            'totals': {
                'subtotal': float(order.subtotal),
                'tax_amount': float(order.tax_amount),
                'total_amount': float(order.total_amount)
            },
            'payment': {
                'method': order.payment_method,
                'reference': payment.transaction_id if payment else '',
                'amount': float(payment.amount) if payment else float(order.total_amount)
            }
        }

        # Add items
        for item in order.items.all():
            invoice_data['items'].append({
                'product_title': item.product.title,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total': float(item.get_total())
            })

        return Response(invoice_data)

    except Exception as e:
        logger.error(f"Error generating invoice for order {order_id}: {e}")
        return Response(
            {'error': 'Failed to generate invoice'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Webhook endpoints for other payment providers (if needed)
@csrf_exempt
@require_POST
def generic_payment_webhook(request, provider):
    """
    Generic webhook endpoint for other payment providers
    POST /api/payments/webhook/{provider}
    """
    try:
        if provider not in ['stripe', 'paypal', 'flutterwave']:
            return HttpResponse('Provider not supported', status=400)

        # Log the webhook for debugging
        logger.info(f"Webhook received from {provider}: {request.body}")

        # Implement provider-specific webhook handling here
        # This is a placeholder for future payment method implementations

        return HttpResponse('OK')

    except Exception as e:
        logger.error(f"Error processing {provider} webhook: {e}")
        return HttpResponse('ERROR', status=500)