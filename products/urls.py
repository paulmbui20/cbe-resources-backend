from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    # Product endpoints
    path('products/', views.ProductListAPIView.as_view(), name='product-list'),
    path('products/<slug:slug>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
    path('products/create/', views.ProductCreateAPIView.as_view(), name='product-create'),
    path('products/<int:id>/update/', views.ProductUpdateAPIView.as_view(), name='product-update'),
    path('products/<int:id>/delete/', views.ProductDeleteAPIView.as_view(), name='product-delete'),

    # Featured and related products
    path('products/featured/', views.featured_products, name='featured-products'),
    path('products/<slug:slug>/related/', views.related_products, name='related-products'),

    # Category endpoints
    path('categories/', views.CategoryListAPIView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryDetailAPIView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/products/', views.category_products, name='category-products'),

    # Filtering options
    path('subjects/', views.SubjectListAPIView.as_view(), name='subject-list'),
    path('grades/', views.GradeListAPIView.as_view(), name='grade-list'),

    # Search
    path('search/suggestions/', views.search_suggestions, name='search-suggestions'),
]
