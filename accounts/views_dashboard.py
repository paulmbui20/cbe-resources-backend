from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from payments.models import Payment
from .models import DownloadLog
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
        "next": "https://api.example.com/accounts/api/downloads/?page=2",
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


class DownloadHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_history(request):
    """
    Get user's comprehensive download history with analytics

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - status: Filter by download status (success, failed, expired, etc.)
    - days: Filter by days (7, 30, 90, 365)
    - device_type: Filter by device (mobile, tablet, desktop)
    - product: Filter by product name (partial match)

    GET /accounts/api/download-history/
    """
    # Get query parameters
    days_filter = request.GET.get('days')
    status_filter = request.GET.get('status')
    device_filter = request.GET.get('device_type')
    product_filter = request.GET.get('product')

    # Base queryset with user's download logs
    queryset = DownloadLog.objects.filter(
        user=request.user
    ).select_related(
        'order_item__product',
        'order_item__order'
    ).prefetch_related(
        'order_item__product__categories'
    )

    # Apply filters
    if days_filter:
        try:
            days = int(days_filter)
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(created_at__gte=cutoff_date)
        except ValueError:
            pass

    if status_filter:
        queryset = queryset.filter(download_status=status_filter)

    if device_filter:
        device_filter_lower = device_filter.lower()
        if device_filter_lower == 'mobile':
            queryset = queryset.filter(is_mobile=True)
        elif device_filter_lower == 'tablet':
            queryset = queryset.filter(is_tablet=True)
        elif device_filter_lower == 'desktop':
            queryset = queryset.filter(is_mobile=False, is_tablet=False)

    if product_filter:
        queryset = queryset.filter(
            order_item__product__title__icontains=product_filter
        )

    # Get analytics data
    total_downloads = queryset.count()
    successful_downloads = queryset.filter(download_status='success').count()
    failed_downloads = queryset.exclude(download_status='success').count()

    # Device breakdown
    device_stats = {
        'mobile': queryset.filter(is_mobile=True).count(),
        'tablet': queryset.filter(is_tablet=True).count(),
        'desktop': queryset.filter(is_mobile=False, is_tablet=False).count(),
    }

    # Browser breakdown
    browser_stats = queryset.values('browser_family').annotate(
        count=Count('id')
    ).order_by('-count')[:5]

    # Recent activity (last 7 days)
    recent_cutoff = timezone.now() - timedelta(days=7)
    recent_activity = queryset.filter(created_at__gte=recent_cutoff).count()

    # Most downloaded products
    popular_products = queryset.filter(
        download_status='success'
    ).values(
        'order_item__product__title',
        'order_item__product__id'
    ).annotate(
        download_count=Count('id')
    ).order_by('-download_count')[:5]

    # Paginate results
    paginator = DownloadHistoryPagination()
    page = paginator.paginate_queryset(queryset.order_by('-created_at'), request)

    # Serialize the data
    download_logs = []
    for log in page:
        product = log.order_item.product if log.order_item else None
        order = log.order_item.order if log.order_item else None

        # Format file size
        file_size_formatted = None
        if log.file_size:
            size = log.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0 or unit == 'GB':
                    file_size_formatted = f"{size:.2f} {unit}"
                    break
                size /= 1024.0

        download_logs.append({
            'id': str(log.id),
            'product_name': product.title if product else 'Unknown Product',
            'product_id': str(product.id) if product else None,
            'product_categories': [cat.name for cat in product.categories.all()] if product else [],
            'order_number': order.order_number if order else None,
            'download_status': log.download_status,
            'download_status_display': log.get_download_status_display(),
            'created_at': log.created_at,
            'ip_address': log.ip_address,

            # Device information
            'device_info': {
                'browser_family': log.browser_family,
                'browser_version': log.browser_version,
                'os_family': log.os_family,
                'os_version': log.os_version,
                'device_family': log.device_family,
                'device_brand': log.device_brand,
                'device_model': log.device_model,
                'device_type': 'Mobile' if log.is_mobile else 'Tablet' if log.is_tablet else 'Desktop',
            },

            # Security flags
            'security_info': {
                'is_bot': log.is_bot,
                'is_suspicious': log.is_suspicious,
            },

            # Download details
            'file_size': log.file_size,
            'file_size_formatted': file_size_formatted,
            'download_duration': log.download_duration,
            'error_message': log.error_message,
        })

    # Prepare response data
    response_data = {
        'results': download_logs,
        'analytics': {
            'total_downloads': total_downloads,
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'success_rate': round((successful_downloads / total_downloads * 100), 2) if total_downloads > 0 else 0,
            'recent_activity_7_days': recent_activity,
            'device_breakdown': device_stats,
            'top_browsers': list(browser_stats),
            'most_downloaded_products': list(popular_products),
        },
        'filters_applied': {
            'days': days_filter,
            'status': status_filter,
            'device_type': device_filter,
            'product': product_filter,
        }
    }

    return paginator.get_paginated_response(response_data)

