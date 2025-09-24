from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, Category, Subject, Grade, ProductImage, ProductReview

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer"""
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'is_active',
            'product_count', 'parent'
        ]

    def get_product_count(self, obj):
        return obj.get_product_count()


class SubjectSerializer(serializers.ModelSerializer):
    """Subject serializer"""

    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description']


class GradeSerializer(serializers.ModelSerializer):
    """Grade serializer"""

    class Meta:
        model = Grade
        fields = ['id', 'name', 'display_name', 'order']


class VendorSerializer(serializers.ModelSerializer):
    """Vendor/User serializer for products"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'display_name', 'email']

    def get_display_name(self, obj):
        return obj.get_display_name() if hasattr(obj, 'get_display_name') else str(obj)


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'order']


class ProductReviewSerializer(serializers.ModelSerializer):
    """Product review serializer"""
    user = VendorSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user', 'rating', 'title', 'review',
            'is_verified_purchase', 'created_at', 'helpful_count'
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer (minimal fields for list view)"""
    category = serializers.CharField(source='category.name', read_only=True)
    subject = serializers.CharField(source='subject.name', read_only=True)
    level = serializers.CharField(source='grade.display_name', read_only=True)
    type = serializers.CharField(source='product_type', read_only=True)
    image = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_discounted = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'price', 'effective_price',
            'discount_percentage', 'is_discounted', 'is_free', 'type',
            'category', 'subject', 'level', 'image', 'rating_average',
            'rating_count', 'view_count', 'is_featured', 'is_bestseller',
            'created_at'
        ]

    def get_image(self, obj):
        """Return thumbnail URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_effective_price(self, obj):
        return float(obj.get_price())

    def get_discount_percentage(self, obj):
        return obj.get_discount_percentage()

    def get_is_discounted(self, obj):
        return obj.is_discounted()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer (full fields for detail view)"""
    category = CategorySerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    grade = GradeSerializer(read_only=True)
    vendor = VendorSerializer(read_only=True)
    type = serializers.CharField(source='product_type', read_only=True)
    level = serializers.CharField(source='grade.display_name', read_only=True)

    # Images and files
    image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    has_preview = serializers.SerializerMethodField()

    # Pricing
    effective_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_discounted = serializers.SerializerMethodField()

    # Reviews
    reviews = ProductReviewSerializer(many=True, read_only=True)
    review_stats = serializers.SerializerMethodField()

    # Tags
    tags = serializers.StringRelatedField(many=True, read_only=True)

    # File info
    file_info = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'content', 'price',
            'effective_price', 'discount_percentage', 'is_discounted',
            'is_free', 'type', 'category', 'subject', 'grade', 'level',
            'vendor', 'image', 'images', 'has_preview', 'rating_average',
            'rating_count', 'view_count', 'download_count', 'is_featured',
            'is_bestseller', 'tags', 'reviews', 'review_stats', 'file_info',
            'created_at', 'updated_at'
        ]

    def get_image(self, obj):
        """Return thumbnail URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_has_preview(self, obj):
        return bool(obj.preview_file)

    def get_effective_price(self, obj):
        return float(obj.get_price())

    def get_discount_percentage(self, obj):
        return obj.get_discount_percentage()

    def get_is_discounted(self, obj):
        return obj.is_discounted()

    def get_review_stats(self, obj):
        """Get review statistics"""
        reviews = obj.reviews.filter(is_approved=True)
        if not reviews.exists():
            return {
                'average': 0,
                'count': 0,
                'distribution': {i: 0 for i in range(1, 6)}
            }

        # Calculate distribution
        distribution = {i: 0 for i in range(1, 6)}
        for review in reviews:
            distribution[review.rating] += 1

        return {
            'average': float(obj.rating_average),
            'count': obj.rating_count,
            'distribution': distribution
        }

    def get_file_info(self, obj):
        """Get file information"""
        return obj.get_file_info()


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product serializer for create/update operations"""

    class Meta:
        model = Product
        fields = [
            'title', 'description', 'content', 'category', 'subject', 'grade',
            'product_type', 'price', 'is_free', 'discount_price', 'preview_file',
            'main_file', 'thumbnail', 'tags'
        ]

    def validate(self, data):
        """Custom validation"""
        if data.get('is_free') and data.get('price', 0) > 0:
            raise serializers.ValidationError(
                "Free products cannot have a price greater than 0"
            )

        if data.get('discount_price') and data.get('discount_price') >= data.get('price', 0):
            raise serializers.ValidationError(
                "Discount price must be less than regular price"
            )

        return data

    def create(self, validated_data):
        # Set vendor to current user
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)


# Serializers for filtering and search
class ProductFilterSerializer(serializers.Serializer):
    """Serializer for product filtering parameters"""
    q = serializers.CharField(required=False, help_text="Search query")
    type = serializers.ChoiceField(
        choices=Product.PRODUCT_TYPES,
        required=False,
        help_text="Product type"
    )
    category = serializers.CharField(required=False, help_text="Category slug")
    subject = serializers.IntegerField(required=False, help_text="Subject ID")
    grade = serializers.IntegerField(required=False, help_text="Grade ID")
    price_min = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    price_max = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    is_free = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            'title', '-title', 'price', '-price', 'created_at', '-created_at',
            'rating_average', '-rating_average', 'view_count', '-view_count'
        ],
        required=False,
        default='-created_at'
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class PaginatedProductResponse(serializers.Serializer):
    """Serializer for paginated product response"""
    items = ProductListSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()