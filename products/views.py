from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, Category, Subject, Grade, ProductViewHistory
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductFilterSerializer,
    CategorySerializer,
    SubjectSerializer,
    GradeSerializer,
    PaginatedProductResponse
)
from .utils import get_client_ip


class CustomPagination(PageNumberPagination):
    """Custom pagination for products"""
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 100
    page_query_param = 'page'


class ProductListAPIView(generics.ListAPIView):
    """
    List products with search and filtering
    GET /api/products?q=search&type=note&page=1&pageSize=20
    """
    serializer_class = ProductListSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'content', 'tags__name']
    ordering_fields = ['title', 'price', 'created_at', 'rating_average', 'view_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get filtered queryset"""
        queryset = Product.objects.filter(status='approved').select_related(
            'vendor', 'category', 'subject', 'grade'
        ).prefetch_related('tags')

        # Get query parameters
        query = self.request.query_params.get('q', '')
        product_type = self.request.query_params.get('type', '')
        category_slug = self.request.query_params.get('category', '')
        subject_id = self.request.query_params.get('subject', '')
        grade_id = self.request.query_params.get('grade', '')
        is_free = self.request.query_params.get('is_free', '')
        is_featured = self.request.query_params.get('is_featured', '')
        price_min = self.request.query_params.get('price_min', '')
        price_max = self.request.query_params.get('price_max', '')

        # Apply filters
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()

        if product_type:
            # Map frontend types to backend types
            type_mapping = {
                'note': 'notes',
                'scheme': 'scheme',
                'exam': 'assessment',
                'revision': 'guide',
                'curriculum': 'curriculum',
                'report': 'assessment',
                'lesson': 'lesson_plan'
            }
            backend_type = type_mapping.get(product_type, product_type)
            queryset = queryset.filter(product_type=backend_type)

        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug, is_active=True)
                # Include subcategories
                categories = category.get_descendants(include_self=True)
                queryset = queryset.filter(category__in=categories)
            except Category.DoesNotExist:
                pass

        if subject_id:
            try:
                queryset = queryset.filter(subject_id=int(subject_id))
            except (ValueError, TypeError):
                pass

        if grade_id:
            try:
                queryset = queryset.filter(grade_id=int(grade_id))
            except (ValueError, TypeError):
                pass

        if is_free.lower() in ['true', '1']:
            queryset = queryset.filter(is_free=True)
        elif is_free.lower() in ['false', '0']:
            queryset = queryset.filter(is_free=False)

        if is_featured.lower() in ['true', '1']:
            queryset = queryset.filter(is_featured=True)

        if price_min:
            try:
                queryset = queryset.filter(price__gte=float(price_min))
            except (ValueError, TypeError):
                pass

        if price_max:
            try:
                queryset = queryset.filter(price__lte=float(price_max))
            except (ValueError, TypeError):
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        """Custom list response to match frontend expectations"""
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)

            page_size = len(serializer.data)
            total = paginated_response.data['count']

            total_pages = 0
            if page_size > 0:
                total_pages = (total // page_size) + (1 if total % page_size else 0)

            return Response({
                'items': serializer.data,
                'total': total,
                'page': int(request.query_params.get('page', 1)),
                'pageSize': page_size,
                'totalPages': total_pages,
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'items': serializer.data,
            'total': len(serializer.data),
            'page': 1,
            'pageSize': len(serializer.data),
            'totalPages': 1
        })


class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    Get product details by slug
    GET /api/products/{slug}
    """
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return Product.objects.filter(status='approved').select_related(
            'vendor', 'category', 'subject', 'grade'
        ).prefetch_related('reviews__user', 'images', 'tags')

    def retrieve(self, request, *args, **kwargs):
        """Custom retrieve with view tracking"""
        instance = self.get_object()

        # Track product view (only if not the vendor viewing their own product)
        if not request.user.is_authenticated or request.user != instance.vendor:
            instance.increment_views()

            # Log detailed view for analytics
            ProductViewHistory.objects.create(
                product=instance,
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referrer=request.META.get('HTTP_REFERER', '')
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductCreateAPIView(generics.CreateAPIView):
    """
    Create a new product
    POST /api/products
    """
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)


class ProductUpdateAPIView(generics.UpdateAPIView):
    """
    Update a product
    PUT/PATCH /api/products/{id}
    """
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Only allow users to update their own products
        return Product.objects.filter(vendor=self.request.user)


class ProductDeleteAPIView(generics.DestroyAPIView):
    """
    Delete a product
    DELETE /api/products/{id}
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Only allow users to delete their own products
        return Product.objects.filter(vendor=self.request.user)


class CategoryListAPIView(generics.ListAPIView):
    """
    List all active categories
    GET /api/categories
    """
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True).order_by('order', 'name')


class CategoryDetailAPIView(generics.RetrieveAPIView):
    """
    Get category details with products
    GET /api/categories/{slug}
    """
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    queryset = Category.objects.filter(is_active=True)


@api_view(['GET'])
def category_products(request, slug):
    """
    Get products in a category (including subcategories)
    GET /api/categories/{slug}/products
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # Get products in this category and subcategories
    categories = category.get_descendants(include_self=True)
    products = Product.objects.filter(
        category__in=categories,
        status='approved'
    ).select_related('vendor', 'category', 'subject', 'grade')

    # Apply additional filters from query params
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(content__icontains=query)
        )

    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('pageSize', 20))

    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page)

    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={'request': request}
    )

    return Response({
        'items': serializer.data,
        'total': paginator.count,
        'page': page,
        'pageSize': len(serializer.data),
        'totalPages': paginator.num_pages,
        'category': CategorySerializer(category, context={'request': request}).data
    })


class SubjectListAPIView(generics.ListAPIView):
    """
    List all active subjects
    GET /api/subjects
    """
    serializer_class = SubjectSerializer
    queryset = Subject.objects.filter(is_active=True).order_by('name')


class GradeListAPIView(generics.ListAPIView):
    """
    List all active grades
    GET /api/grades
    """
    serializer_class = GradeSerializer
    queryset = Grade.objects.filter(is_active=True).order_by('order')


@api_view(['GET'])
def featured_products(request):
    """
    Get featured products
    GET /api/products/featured
    """
    products = Product.objects.filter(
        status='approved',
        is_featured=True
    ).select_related('vendor', 'category', 'subject', 'grade')[:12]

    serializer = ProductListSerializer(
        products,
        many=True,
        context={'request': request}
    )

    return Response({
        'items': serializer.data,
        'total': len(serializer.data)
    })


@api_view(['GET'])
def related_products(request, slug):
    """
    Get related products for a given product
    GET /api/products/{slug}/related
    """
    product = get_object_or_404(Product, slug=slug, status='approved')

    related = Product.objects.filter(
        Q(category=product.category) | Q(subject=product.subject),
        status='approved'
    ).exclude(id=product.id).select_related(
        'vendor', 'category', 'subject', 'grade'
    )[:6]

    serializer = ProductListSerializer(
        related,
        many=True,
        context={'request': request}
    )

    return Response({
        'items': serializer.data,
        'total': len(serializer.data)
    })


@api_view(['GET'])
def search_suggestions(request):
    """
    Get search suggestions
    GET /api/search/suggestions?q=query
    """
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return Response({'suggestions': []})

    # Get product titles that match
    products = Product.objects.filter(
        title__icontains=query,
        status='approved'
    ).values_list('title', flat=True)[:10]

    # Get category names that match
    categories = Category.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:5]

    # Get subject names that match
    subjects = Subject.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:5]

    suggestions = list(set(list(products) + list(categories) + list(subjects)))

    return Response({
        'suggestions': suggestions[:15]
    })