from django.db.models import Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from products.serializers import CategorySerializer, SubjectSerializer, GradeSerializer


@api_view(['GET'])
def api_stats(request):
    """
    Get general API statistics
    GET /api/stats
    """
    from .models import Product, Category, Subject

    stats = {
        'total_products': Product.objects.filter(status='approved').count(),
        'total_categories': Category.objects.filter(is_active=True).count(),
        'total_subjects': Subject.objects.filter(is_active=True).count(),
        'featured_products': Product.objects.filter(status='approved', is_featured=True).count(),
        'free_products': Product.objects.filter(status='approved', is_free=True).count(),
        'product_types': Product.objects.filter(status='approved').values('product_type').annotate(
            count=Count('id')
        ).order_by('-count'),
        'top_categories': Category.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__status='approved'))
        ).order_by('-product_count')[:5],
    }

    return Response(stats)


@api_view(['GET'])
def product_filters(request):
    """
    Get all available filter options
    GET /api/filters
    """
    from .models import Product, Category, Subject, Grade

    filters = {
        'types': [{'value': choice[0], 'label': choice[1]} for choice in Product.PRODUCT_TYPES],
        'categories': CategorySerializer(
            Category.objects.filter(is_active=True).order_by('name'),
            many=True,
            context={'request': request}
        ).data,
        'subjects': SubjectSerializer(
            Subject.objects.filter(is_active=True).order_by('name'),
            many=True
        ).data,
        'grades': GradeSerializer(
            Grade.objects.filter(is_active=True).order_by('order'),
            many=True
        ).data,
        'price_ranges': [
            {'value': 'free', 'label': 'Free'},
            {'value': '0-100', 'label': '0 - 100 KSH'},
            {'value': '100-500', 'label': '100 - 500 KSH'},
            {'value': '500-1000', 'label': '500 - 1000 KSH'},
            {'value': '1000+', 'label': '1000+ KSH'},
        ],
        'sort_options': [
            {'value': '-created_at', 'label': 'Newest First'},
            {'value': 'created_at', 'label': 'Oldest First'},
            {'value': 'title', 'label': 'Title A-Z'},
            {'value': '-title', 'label': 'Title Z-A'},
            {'value': 'price', 'label': 'Price Low to High'},
            {'value': '-price', 'label': 'Price High to Low'},
            {'value': '-rating_average', 'label': 'Highest Rated'},
            {'value': '-view_count', 'label': 'Most Popular'},
        ]
    }

    return Response(filters)