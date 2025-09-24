from django.contrib import admin
from .models import Payment, MPesaPayment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('order__order_number', 'user__email', 'external_reference', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at', 'processed_at')

    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'user', 'amount', 'currency', 'payment_method')
        }),
        ('External References', {
            'fields': ('external_reference', 'transaction_id')
        }),
        ('Status', {
            'fields': ('status', 'failure_reason')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(MPesaPayment)
class MPesaPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment', 'phone_number', 'amount', 'mpesa_receipt_number', 'result_code', 'created_at')
    list_filter = ('result_code', 'created_at')
    search_fields = ('phone_number', 'mpesa_receipt_number', 'checkout_request_id', 'payment__order__order_number')
    readonly_fields = ('created_at', 'updated_at')
