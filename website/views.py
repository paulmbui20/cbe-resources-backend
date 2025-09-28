from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WebsiteInfo, Contact, TermsOfService, PrivacyPolicy, FAQ, Testimonials
from .serializers import (
    WebsiteInfoSerializer, ContactSerializer, ContactCreateSerializer,
    TermsOfServiceSerializer, PrivacyPolicySerializer, FAQSerializer, TestimonialSerializer
)


class WebsiteInfoAPIView(APIView):
    """
    Get website information with caching
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Use cache similar to context processor
        website_info = cache.get_or_set(
            'website_info',
            lambda: WebsiteInfo.objects.first(),
            timeout=3600  # 1 hour cache
        )

        if not website_info:
            return Response(
                {"detail": "Website information not available"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = WebsiteInfoSerializer(website_info, context={'request': request})
        return Response(serializer.data)


class ContactCreateAPIView(generics.CreateAPIView):
    """
    Create a new contact message
    """
    queryset = Contact.objects.all()
    serializer_class = ContactCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Your message has been sent successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"errors": serializer.errors, "message": "Error in form data"},
            status=status.HTTP_400_BAD_REQUEST
        )


class ContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contacts (admin use)
    """
    queryset = Contact.objects.all().order_by('-submitted_at')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'is_read']
    search_fields = ['full_name', 'email', 'message']
    ordering_fields = ['submitted_at', 'priority']
    ordering = ['-submitted_at']

    def update(self, request, *args, **kwargs):
        """Allow partial updates for marking as read"""
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class TermsOfServiceAPIView(APIView):
    """
    Get active Terms of Service with caching
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            terms = cache.get_or_set(
                "active_tos",
                lambda: TermsOfService.objects.get(active=True),
                timeout=86400  # 24 hours cache
            )

            # Create cache key based on last update
            cache_key = f"tos_data_{int(terms.last_update.timestamp())}"
            cached_data = cache.get(cache_key)

            if not cached_data:
                serializer = TermsOfServiceSerializer(terms, context={'request': request})
                cached_data = serializer.data
                cache.set(cache_key, cached_data, timeout=86400)

            return Response(cached_data)

        except TermsOfService.DoesNotExist:
            return Response(
                {"detail": "Terms of Service not available"},
                status=status.HTTP_404_NOT_FOUND
            )


class PrivacyPolicyAPIView(APIView):
    """
    Get active Privacy Policy with caching
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            policy = cache.get_or_set(
                "active_privacy",
                lambda: PrivacyPolicy.objects.get(active=True),
                timeout=86400  # 24 hours cache
            )

            # Create cache key based on last update
            cache_key = f"privacy_data_{int(policy.last_update.timestamp())}"
            cached_data = cache.get(cache_key)

            if not cached_data:
                serializer = PrivacyPolicySerializer(policy, context={'request': request})
                cached_data = serializer.data
                cache.set(cache_key, cached_data, timeout=86400)

            return Response(cached_data)

        except PrivacyPolicy.DoesNotExist:
            return Response(
                {"detail": "Privacy Policy not available"},
                status=status.HTTP_404_NOT_FOUND
            )


class FAQListAPIView(generics.ListAPIView):
    """
    List active FAQs with caching
    """
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Use cache similar to original view
        return cache.get_or_set(
            "faqs_cache",
            lambda: FAQ.objects.filter(is_active=True)[:15],
            timeout=2419200  # 28 days cache as in original
        )


class FAQViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing FAQs (admin use)
    """
    queryset = FAQ.objects.all().order_by('order')
    serializer_class = FAQSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['question', 'answer']
    ordering_fields = ['order', 'created_at', 'updated_at']
    ordering = ['order']

    def create(self, request, *args, **kwargs):
        """Clear FAQ cache when creating new FAQ"""
        response = super().create(request, *args, **kwargs)
        cache.delete("faqs_cache")
        return response

    def update(self, request, *args, **kwargs):
        """Clear FAQ cache when updating FAQ"""
        response = super().update(request, *args, **kwargs)
        cache.delete("faqs_cache")
        return response

    def destroy(self, request, *args, **kwargs):
        """Clear FAQ cache when deleting FAQ"""
        response = super().destroy(request, *args, **kwargs)
        cache.delete("faqs_cache")
        return response


class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonials.objects.all().order_by("-date_added")[:5]
    serializer_class = TestimonialSerializer
