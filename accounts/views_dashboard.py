from django.db.models import Count, Sum, Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from payments.models import Payment
from .serializers import (
    UserDashboardSerializer,
    UserDownloadSerializer,
    UserPurchaseSerializer,
    UserOrderSummarySerializer,
    UserPaymentSerializer
)


class UserDashboardView(APIView):
    """
    User dashboard with summary information
    
    Returns a summary of user's activity including counts of orders, purchases,
    downloads, and recent activity.
    
    GET /accounts/api/dashboard/
    
    Sample Response:
    {
        "total_orders": 15,
        "completed_orders": 12,
        "pending_orders": 3,
        "total_spent": 25000,
        "recent_orders": [
            {
                "order_number": "ORD-2023-001",
                "total_amount": 2500,
                "status": "paid",
                "created_at": "2023-12-01T10:30:00Z"
            }
        ],
        "recent_downloads": [
            {
                "product_name": "Grade 4 Mathematics",
                "downloaded_at": "2023-12-02T15:45:00Z"
            }
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserDashboardSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class UserDownloadsView(generics.ListAPIView):
    """
    List user's downloads
    
    Returns a paginated list of all user's downloads with details including
    download URLs, file information, and download counts.
    
    GET /accounts/api/downloads/
    
    Sample Response:
    {
        "count": 25,
        "next": "http://api.example.com/accounts/api/downloads/?page=2",
        "previous": null,
        "results": [
            {
                "product_name": "Grade 5 Science",
                "thumbnail_url": "https://example.com/thumbnails/science.jpg",
                "download_url": "https://example.com/downloads/token/xyz",
                "order_number": "ORD-2023-001",
                "file_type": "PDF",
                "file_size": "25MB",
                "download_count": 3,
                "last_downloaded": "2023-12-01T10:30:00Z"
            }
        ]
    }
    """
    serializer_class = UserDownloadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return OrderItem.objects.filter(
            order__user=self.request.user,
            order__status='paid',
            download_token__isnull=False
        ).select_related(
            'product', 'order'
        ).order_by('-updated_at')


class UserPurchasesView(generics.ListAPIView):
    """
    List user's purchases
    
    Returns a paginated list of all products purchased by the user with
    details including product information, purchase date, and download status.
    
    GET /accounts/api/purchases/
    
    Sample Response:
    {
        "count": 10,
        "next": null,
        "previous": null,
        "results": [
            {
                "product_name": "Grade 3 English",
                "thumbnail_url": "https://example.com/thumbnails/english.jpg",
                "product_type": "E-Book",
                "purchase_date": "2023-12-01T10:30:00Z",
                "order_number": "ORD-2023-001",
                "price": 1500,
                "download_available": true,
                "download_expiry": "2024-12-01T10:30:00Z"
            }
        ]
    }
    """
    serializer_class = UserPurchaseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return OrderItem.objects.filter(
            order__user=self.request.user,
            order__status__in=['paid', 'processing', 'refunded']
        ).select_related(
            'product', 'order'
        ).order_by('-created_at')


class UserOrdersView(generics.ListAPIView):
    """
    List user's orders
    
    Returns a paginated list of all user's orders with summary information
    including status, total amount, and item count.
    
    GET /accounts/api/orders/
    
    Sample Response:
    {
        "count": 15,
        "next": null,
        "previous": null,
        "results": [
            {
                "order_number": "ORD-2023-001",
                "created_at": "2023-12-01T10:30:00Z",
                "status": "paid",
                "total_amount": 2500,
                "item_count": 3,
                "payment_method": "M-Pesa",
                "items": [
                    {
                        "product_name": "Grade 4 Mathematics",
                        "quantity": 1,
                        "price": 1500
                    }
                ]
            }
        ]
    }
    """
    serializer_class = UserOrderSummarySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related(
            'items'
        ).order_by('-created_at')


class UserPaymentsView(generics.ListAPIView):
    """
    List user's payment history
    
    Returns a paginated list of all user's payment transactions with
    details including payment method, status, and amount.
    
    GET /accounts/api/payments/
    
    Sample Response:
    {
        "count": 20,
        "next": null,
        "previous": null,
        "results": [
            {
                "payment_id": "PAY-2023-001",
                "order_number": "ORD-2023-001",
                "amount": 2500,
                "currency": "KES",
                "payment_method": "M-Pesa",
                "status": "completed",
                "transaction_id": "MPESA123456",
                "created_at": "2023-12-01T10:30:00Z"
            }
        ]
    }
    """
    serializer_class = UserPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(
            user=self.request.user
        ).select_related(
            'order'
        ).order_by('-created_at')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """
    Get user statistics
    
    Returns aggregated statistics about the user's activity including
    total spent, download counts, and purchase metrics.
    
    GET /accounts/api/stats/
    
    Sample Response:
    {
        "total_orders": 15,
        "completed_orders": 12,
        "pending_orders": 3,
        "total_spent": 25000,
        "total_purchases": 20,
        "total_downloads": 45,
        "recent_activity": {
            "recent_orders": [
                {
                    "id": 1,
                    "order_number": "ORD-2023-001",
                    "created_at": "2023-12-01T10:30:00Z",
                    "status": "paid",
                    "total_amount": 2500
                }
            ],
            "recent_payments": [
                {
                    "id": 1,
                    "amount": 2500,
                    "payment_method": "M-Pesa",
                    "status": "completed",
                    "created_at": "2023-12-01T10:30:00Z"
                }
            ]
        }
    }
    """
    # Get user's orders
    orders = Order.objects.filter(user=request.user)
    
    # Calculate statistics
    stats = {
        'total_orders': orders.count(),
        'completed_orders': orders.filter(status='paid').count(),
        'pending_orders': orders.filter(status='pending').count(),
        
        'total_spent': Payment.objects.filter(
            user=request.user,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        
        'total_purchases': OrderItem.objects.filter(
            order__user=request.user,
            order__status='paid'
        ).count(),
        
        'total_downloads': OrderItem.objects.filter(
            order__user=request.user,
            order__status='paid',
            download_token__isnull=False
        ).aggregate(total=Sum('download_count'))['total'] or 0,
        
        'recent_activity': {
            'recent_orders': orders.order_by('-created_at')[:3].values('id', 'order_number', 'created_at', 'status', 'total_amount'),
            'recent_payments': Payment.objects.filter(user=request.user).order_by('-created_at')[:3].values('id', 'amount', 'payment_method', 'status', 'created_at'),
        }
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_history(request):
    """
    Get user's download history
    
    Returns detailed information about the user's download activity including
    timestamps, IP addresses, and device information.
    
    GET /accounts/api/download-history/
    
    Sample Response:
    [
        {
            "product_name": "Grade 4 Mathematics",
            "order_number": "ORD-2023-001",
            "download_count": 3,
            "last_downloaded": "2023-12-01T10:30:00Z",
            "download_expiry": "2024-12-01T10:30:00Z"
        }
    ]
    """
    # This would require a DownloadLog model to track download activity
    # For now, we'll return a simplified version based on OrderItem download_count
    
    downloads = OrderItem.objects.filter(
        order__user=request.user,
        order__status='paid',
        download_token__isnull=False,
        download_count__gt=0
    ).select_related(
        'product', 'order'
    ).order_by('-updated_at')
    
    data = [{
        'product_name': item.product.name if item.product else 'Unknown Product',
        'order_number': item.order.order_number if item.order else None,
        'download_count': item.download_count,
        'last_downloaded': item.updated_at,
        'download_expiry': item.download_expiry
    } for item in downloads]
    
    return Response(data)