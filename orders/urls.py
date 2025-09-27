from django.urls import path

from payments.views import order_invoice, request_refund
from . import views, utils

app_name = 'orders'

urlpatterns = [
    # Order endpoints
    path('orders/', views.OrderListAPIView.as_view(), name='order-list'),
    path('orders/<uuid:id>/', views.OrderDetailAPIView.as_view(), name='order-detail'),
    path('orders/create/', views.OrderCreateAPIView.as_view(), name='order-create'),
    path('orders/quick-checkout/', views.quick_checkout, name='quick-checkout'),
    path('orders/<uuid:order_id>/checkout/', views.checkout_details, name='checkout-details'),
    path('orders/<uuid:order_id>/process-free/', views.process_free_order, name='process-free-order'),
    path('orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('orders/<uuid:order_id>/invoice/', order_invoice, name='order-invoice'),
    path('orders/<uuid:order_id>/refund/', request_refund, name='request-refund'),

    # Download endpoints
    path('downloads/<str:token>/', utils.download_file, name='download-file'),

    # Cart endpoints
    path('cart/', views.CartAPIView.as_view(), name='cart'),
    path('cart/add/', views.add_to_cart, name='add-to-cart'),
    path('cart/items/<uuid:item_id>/', views.remove_from_cart, name='remove-from-cart'),
]
