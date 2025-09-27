from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from .models import CustomUser, DownloadLog


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'get_full_name', 'is_vendor', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_vendor', 'is_verified', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'is_vendor', 'is_verified')}),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = 'Full Name'

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        return "No Image"

    avatar_preview.short_description = "Avatar"


class DeviceTypeFilter(SimpleListFilter):
    title = 'Device Type'
    parameter_name = 'device_type'

    def lookups(self, request, model_admin):
        return (
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('desktop', 'Desktop'),
            ('bot', 'Bot'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'mobile':
            return queryset.filter(is_mobile=True)
        elif self.value() == 'tablet':
            return queryset.filter(is_tablet=True)
        elif self.value() == 'desktop':
            return queryset.filter(is_mobile=False, is_tablet=False, is_bot=False)
        elif self.value() == 'bot':
            return queryset.filter(is_bot=True)


class DownloadStatusFilter(SimpleListFilter):
    title = 'Download Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return DownloadLog._meta.get_field('download_status').choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(download_status=self.value())


class SuspiciousFilter(SimpleListFilter):
    title = 'Security Status'
    parameter_name = 'security'

    def lookups(self, request, model_admin):
        return (
            ('suspicious', 'Suspicious'),
            ('bot', 'Bot'),
            ('clean', 'Clean'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'suspicious':
            return queryset.filter(is_suspicious=True)
        elif self.value() == 'bot':
            return queryset.filter(is_bot=True)
        elif self.value() == 'clean':
            return queryset.filter(is_suspicious=False, is_bot=False)


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at_formatted',
        'user_link',
        'product_name',
        'download_status_badge',
        'device_info_display',
        'ip_address',
        'file_size_display',
        'duration_display',
        'security_flags',
    ]

    list_filter = [
        'download_status',
        DeviceTypeFilter,
        DownloadStatusFilter,
        SuspiciousFilter,
        'browser_family',
        'os_family',
        'created_at',
        'is_mobile',
        'is_tablet',
        'is_bot',
        'is_suspicious',
    ]

    search_fields = [
        'user__email',
        'user__username',
        'order_item__product__title',
        'order_item__order__order_number',
        'ip_address',
        'browser_family',
        'os_family',
        'device_family',
        'user_agent',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'user_agent_formatted',
        'detailed_device_info',
        'download_location_map',
    ]

    fieldsets = (
        ('Download Information', {
            'fields': (
                'user',
                'order_item',
                'download_status',
                'created_at',
                'file_size',
                'download_duration',
                'error_message',
            )
        }),
        ('User Agent & Device', {
            'fields': (
                'user_agent_formatted',
                'detailed_device_info',
                'browser_family',
                'browser_version',
                'os_family',
                'os_version',
                'device_family',
                'device_brand',
                'device_model',
            )
        }),
        ('Device Capabilities', {
            'fields': (
                'is_mobile',
                'is_tablet',
                'is_bot',
                'is_suspicious',
            )
        }),
        ('Network Information', {
            'fields': (
                'ip_address',
                'download_location_map',
            )
        }),
    )

    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    actions = ['mark_as_suspicious', 'mark_as_clean', 'export_to_csv']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user',
            'order_item__product',
            'order_item__order'
        )

    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    created_at_formatted.short_description = 'Download Time'
    created_at_formatted.admin_order_field = 'created_at'

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def product_name(self, obj):
        if obj.order_item and obj.order_item.product:
            url = reverse('admin:products_product_change', args=[obj.order_item.product.pk])
            return format_html('<a href="{}">{}</a>', url, obj.order_item.product.title[:50])
        return 'Unknown Product'

    product_name.short_description = 'Product'

    def download_status_badge(self, obj):
        colors = {
            'success': 'green',
            'failed': 'red',
            'expired': 'orange',
            'invalid': 'red',
            'limit_exceeded': 'purple'
        }
        color = colors.get(obj.download_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_download_status_display()
        )

    download_status_badge.short_description = 'Status'
    download_status_badge.admin_order_field = 'download_status'

    def device_info_display(self, obj):
        device_type = 'Mobile' if obj.is_mobile else 'Tablet' if obj.is_tablet else 'Desktop'
        if obj.is_bot:
            device_type = 'Bot'

        return format_html(
            '<div title="{} {} on {} {}">{}<br><small>{} {}</small></div>',
            obj.browser_family,
            obj.browser_version,
            obj.os_family,
            obj.os_version,
            device_type,
            obj.browser_family,
            obj.os_family
        )

    device_info_display.short_description = 'Device Info'

    def file_size_display(self, obj):
        if not obj.file_size:
            return '-'

        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0 or unit == 'GB':
                return f"{size:.2f} {unit}"
            size /= 1024.0

    file_size_display.short_description = 'File Size'
    file_size_display.admin_order_field = 'file_size'

    def duration_display(self, obj):
        if not obj.download_duration:
            return '-'

        duration = obj.download_duration
        if duration < 1:
            return f"{duration * 1000:.0f}ms"
        elif duration < 60:
            return f"{duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"

    duration_display.short_description = 'Duration'
    duration_display.admin_order_field = 'download_duration'

    def security_flags(self, obj):
        flags = []
        if obj.is_bot:
            flags.append('<span style="color: orange;">BOT</span>')
        if obj.is_suspicious:
            flags.append('<span style="color: red;">SUSPICIOUS</span>')

        return format_html(' '.join(flags)) if flags else '-'

    security_flags.short_description = 'Security'

    def user_agent_formatted(self, obj):
        if not obj.user_agent:
            return 'No User Agent'

        # Truncate long user agents for display
        ua = obj.user_agent
        if len(ua) > 200:
            ua = ua[:200] + '...'

        return format_html('<pre style="white-space: pre-wrap;">{}</pre>', ua)

    user_agent_formatted.short_description = 'User Agent'

    def detailed_device_info(self, obj):
        info = {
            'Browser': f"{obj.browser_family} {obj.browser_version}",
            'Operating System': f"{obj.os_family} {obj.os_version}",
            'Device': f"{obj.device_family}",
            'Brand': obj.device_brand or 'Unknown',
            'Model': obj.device_model or 'Unknown',
            'Mobile': 'Yes' if obj.is_mobile else 'No',
            'Tablet': 'Yes' if obj.is_tablet else 'No',
            'Bot': 'Yes' if obj.is_bot else 'No',
            'Suspicious': 'Yes' if obj.is_suspicious else 'No',
        }

        html = '<table style="width: 100%;">'
        for key, value in info.items():
            html += f'<tr><td style="font-weight: bold; padding: 2px 10px 2px 0;">{key}:</td><td style="padding: 2px;">{value}</td></tr>'
        html += '</table>'

        return format_html(html)

    detailed_device_info.short_description = 'Device Details'

    def download_location_map(self, obj):
        # Placeholder for IP geolocation map
        # You could integrate with Google Maps or other mapping services
        return format_html(
            '<div>IP: <strong>{}</strong><br>'
            '<small>Geolocation data would appear here</small></div>',
            obj.ip_address
        )

    download_location_map.short_description = 'Location'

    # Admin Actions
    def mark_as_suspicious(self, request, queryset):
        updated = queryset.update(is_suspicious=True)
        self.message_user(request, f'{updated} download logs marked as suspicious.')

    mark_as_suspicious.short_description = 'Mark selected logs as suspicious'

    def mark_as_clean(self, request, queryset):
        updated = queryset.update(is_suspicious=False)
        self.message_user(request, f'{updated} download logs marked as clean.')

    mark_as_clean.short_description = 'Mark selected logs as clean'

    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="download_logs.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'User', 'Product', 'Status', 'IP Address',
            'Browser', 'OS', 'Device Type', 'File Size', 'Duration',
            'Is Bot', 'Is Suspicious'
        ])

        for log in queryset:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.email,
                log.order_item.product.title if log.order_item and log.order_item.product else 'Unknown',
                log.get_download_status_display(),
                log.ip_address,
                f"{log.browser_family} {log.browser_version}",
                f"{log.os_family} {log.os_version}",
                'Mobile' if log.is_mobile else 'Tablet' if log.is_tablet else 'Desktop',
                log.file_size or 0,
                log.download_duration or 0,
                log.is_bot,
                log.is_suspicious,
            ])

        return response

    export_to_csv.short_description = 'Export selected logs to CSV'







