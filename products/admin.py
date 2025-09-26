from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import Category, Subject, Grade, Product, ProductImage, ProductReview


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'product_count', 'created_at')
    list_filter = ('is_active', 'created_at', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')

    def product_count(self, obj):
        return obj.get_product_count()

    product_count.short_description = 'Products'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'order', 'is_active')
    list_filter = ('is_active',)
    ordering = ('order',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'order')


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    readonly_fields = ('user', 'rating', 'created_at')
    fields = ('user', 'rating', 'title', 'is_approved', 'created_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'category', 'subject', 'grade', 'price', 'status', 'view_count', 'created_at')
    list_filter = ('status', 'is_free', 'is_featured', 'product_type', 'category', 'subject', 'grade', 'created_at')
    search_fields = ('title', 'description', 'vendor__email', 'vendor__first_name', 'vendor__last_name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'view_count', 'download_count', 'rating_average', 'rating_count')
    inlines = [ProductImageInline, ProductReviewInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'content', 'thumbnail')
        }),
        ('Classification', {
            'fields': ('category', 'subject', 'grade', 'product_type', 'tags')
        }),
        ('Vendor & Files', {
            'fields': ('vendor', 'main_file', 'preview_file')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'is_free')
        }),
        ('Status & Moderation', {
            'fields': ('status', 'rejection_reason', 'approved_by', 'approved_at')
        }),
        ('Features & Analytics', {
            'fields': ('is_featured', 'is_bestseller', 'view_count', 'download_count', 'rating_average', 'rating_count')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['approve_products', 'reject_products', 'feature_products']

    def approve_products(self, request, queryset):
        """Bulk approve products"""
        from django.utils import timezone
        updated = queryset.update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} products approved.')

    approve_products.short_description = "Approve selected products"

    def reject_products(self, request, queryset):
        """Bulk reject products"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} products rejected.')

    reject_products.short_description = "Reject selected products"

    def feature_products(self, request, queryset):
        """Mark products as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')

    feature_products.short_description = "Mark as featured"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vendor', 'category', 'subject', 'grade')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_approved', 'is_verified_purchase', 'created_at')
    search_fields = ('product__title', 'user__email', 'title', 'review')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')

