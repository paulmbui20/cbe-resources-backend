def get_client_ip(request):
    """Get the client's IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



# Product type mapping helper
FRONTEND_TO_BACKEND_TYPE_MAPPING = {
    'note': 'notes',
    'scheme': 'scheme',
    'exam': 'assessment',
    'revision': 'guide',
    'curriculum': 'curriculum',
    'report': 'assessment',
    'lesson': 'lesson_plan'
}

BACKEND_TO_FRONTEND_TYPE_MAPPING = {v: k for k, v in FRONTEND_TO_BACKEND_TYPE_MAPPING.items()}


def map_product_type_to_frontend(backend_type):
    """Convert backend product type to frontend type"""
    return BACKEND_TO_FRONTEND_TYPE_MAPPING.get(backend_type, backend_type)


def map_product_type_to_backend(frontend_type):
    """Convert frontend product type to backend type"""
    return FRONTEND_TO_BACKEND_TYPE_MAPPING.get(frontend_type, frontend_type)


# Custom exception handler for better error responses
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """Custom exception handler for API errors"""
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'An error occurred',
            'details': response.data
        }

        if response.status_code == 404:
            custom_response_data['message'] = 'Resource not found'
        elif response.status_code == 400:
            custom_response_data['message'] = 'Invalid request data'
        elif response.status_code == 401:
            custom_response_data['message'] = 'Authentication required'
        elif response.status_code == 403:
            custom_response_data['message'] = 'Permission denied'
        elif response.status_code == 500:
            custom_response_data['message'] = 'Internal server error'

        response.data = custom_response_data

    return response


# Middleware for API request logging (optional)
import logging
import json

logger = logging.getLogger('api')


class APILoggingMiddleware:
    """Middleware to log API requests and responses"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request
        if request.path.startswith('/api/'):
            logger.info(f"API Request: {request.method} {request.path}")
            if request.body and len(request.body) < 1000:  # Don't log large files
                try:
                    body = json.loads(request.body.decode('utf-8'))
                    logger.info(f"Request Body: {body}")
                except:
                    pass

        response = self.get_response(request)

        # Log response
        if request.path.startswith('/api/'):
            logger.info(f"API Response: {response.status_code}")

        return response


# Database optimization helpers
from django.db import connection


def get_query_count():
    """Get the number of database queries executed"""
    return len(connection.queries)


def log_queries():
    """Decorator to log database queries for a view"""

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            initial_queries = get_query_count()
            response = view_func(request, *args, **kwargs)
            query_count = get_query_count() - initial_queries
            logger.info(f"View {view_func.__name__} executed {query_count} queries")
            return response

        return wrapper

    return decorator