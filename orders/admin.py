from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'unit_price', 'quantity', 'download_count', 'download_expires_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'user__email', 'customer_email', 'payment_reference')
    readonly_fields = ('created_at', 'updated_at', 'subtotal', 'tax_amount', 'total_amount')
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Customer Details', {
            'fields': ('customer_email', 'customer_phone')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_reference', 'payment_date')
        }),
        ('Totals', {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        ('Additional Info', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_paid', 'mark_as_cancelled']

    def mark_as_paid(self, request, queryset):
        """Mark orders as paid"""
        for order in queryset.filter(status='pending'):
            order.mark_as_paid()
        count = queryset.filter(status='pending').count()
        self.message_user(request, f'{count} orders marked as paid.')

    mark_as_paid.short_description = "Mark as paid"

    def mark_as_cancelled(self, request, queryset):
        """Mark orders as cancelled"""
        updated = queryset.filter(status__in=['pending', 'processing']).update(status='cancelled')
        self.message_user(request, f'{updated} orders cancelled.')

    mark_as_cancelled.short_description = "Cancel orders"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'unit_price', 'download_count', 'download_limit', 'download_expires_at')
    list_filter = ('download_expires_at', 'created_at')
    search_fields = ('product__title', 'order__order_number', 'order__user__email')
    readonly_fields = ('created_at', 'updated_at')
