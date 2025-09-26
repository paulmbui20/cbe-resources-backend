from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .health import health_check
from .views import (
    WebsiteInfoAPIView, ContactCreateAPIView, ContactViewSet,
    TermsOfServiceAPIView, PrivacyPolicyAPIView,
    FAQListAPIView, FAQViewSet, TestimonialViewSet
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')

# API URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
    path("healthcheck", health_check, name="healthcheck"),
    # Public API endpoints
    path('api/website-info/', WebsiteInfoAPIView.as_view(), name='website-info-api'),
    path('api/contact/', ContactCreateAPIView.as_view(), name='contact-create-api'),
    path('api/terms-of-service/', TermsOfServiceAPIView.as_view(), name='terms-api'),
    path('api/privacy-policy/', PrivacyPolicyAPIView.as_view(), name='privacy-api'),
    path('api/faqs/', FAQListAPIView.as_view(), name='faqs-list-api'),

    # Admin/Management endpoints (require authentication)
    path('api/website/admin/', include(router.urls)),

]
