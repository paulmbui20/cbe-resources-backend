from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    # Product endpoints
    path('', views.ProductListAPIView.as_view(), name='product-list'),
    path('create/', views.ProductCreateAPIView.as_view(), name='product-create'),
    path('featured/', views.featured_products, name='featured-products'),
    path('search/suggestions/', views.search_suggestions, name='search-suggestions'),

    path('<int:id>/update/', views.ProductUpdateAPIView.as_view(), name='product-update'),
    path('<int:id>/delete/', views.ProductDeleteAPIView.as_view(), name='product-delete'),

    # Category endpoints (separate detail vs. products)
    path('categories/', views.CategoryListAPIView.as_view(), name='category-list'),
    path('categories/<slug:slug>/detail/', views.CategoryDetailAPIView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/products/', views.category_products, name='category-products'),

    # Filtering options
    path('subjects/', views.SubjectListAPIView.as_view(), name='subject-list'),
    path('grades/', views.GradeListAPIView.as_view(), name='grade-list'),

    # Related products BEFORE detail (so it doesn’t get eaten by <slug>)
    path('<slug:slug>/related/', views.related_products, name='related-products'),
    path('<slug:slug>/', views.ProductDetailAPIView.as_view(), name='product-detail'),


]
