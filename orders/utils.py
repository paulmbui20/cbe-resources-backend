# User Agent Parsing with ua-parser[regex] - Modern Implementation

# Installation: pip install 'ua-parser[regex]'

import logging
import mimetypes
import os
import time

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ua_parser import user_agent_parser

logger = logging.getLogger(__name__)


def parse_user_agent(user_agent_string):
    """
    Parse user agent using ua-parser with regex engine
    """
    if not user_agent_string:
        return get_default_ua_info()

    try:
        # Parse using ua-parser
        parsed = user_agent_parser.Parse(user_agent_string)

        # Extract browser information
        browser = parsed.get('user_agent', {})
        browser_family = browser.get('family', 'Other')
        browser_version_parts = [
            browser.get('major', ''),
            browser.get('minor', ''),
            browser.get('patch', '')
        ]
        browser_version = '.'.join(filter(None, browser_version_parts)) or 'Unknown'

        # Extract OS information
        os_info = parsed.get('os', {})
        os_family = os_info.get('family', 'Other')
        os_version_parts = [
            os_info.get('major', ''),
            os_info.get('minor', ''),
            os_info.get('patch', ''),
            os_info.get('patch_minor', '')
        ]
        os_version = '.'.join(filter(None, os_version_parts)) or 'Unknown'

        # Extract device information
        device = parsed.get('device', {})
        device_family = device.get('family', 'Other')
        device_brand = device.get('brand')
        device_model = device.get('model')

        # Determine device characteristics
        ua_lower = user_agent_string.lower()

        # Mobile detection
        is_mobile = (
                'mobile' in ua_lower or
                'phone' in ua_lower or
                device_family in ['iPhone', 'Android', 'BlackBerry', 'Windows Phone'] or
                any(mobile_os in os_family for mobile_os in ['Android', 'iOS', 'Windows Phone', 'BlackBerry'])
        )

        # Tablet detection
        is_tablet = (
                'tablet' in ua_lower or
                device_family in ['iPad', 'Android Tablet'] or
                ('android' in ua_lower and 'mobile' not in ua_lower)
        )

        # Bot detection
        is_bot = any(bot_indicator in ua_lower for bot_indicator in [
            'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl',
            'python-requests', 'automated', 'headless', 'phantom'
        ])

        # Touch capability detection
        is_touch_capable = is_mobile or is_tablet or 'touch' in ua_lower

        return {
            'browser_family': browser_family,
            'browser_version': browser_version,
            'browser_major': browser.get('major'),
            'browser_minor': browser.get('minor'),
            'os_family': os_family,
            'os_version': os_version,
            'os_major': os_info.get('major'),
            'os_minor': os_info.get('minor'),
            'device_family': device_family,
            'device_brand': device_brand,
            'device_model': device_model,
            'is_mobile': is_mobile,
            'is_tablet': is_tablet,
            'is_pc': not (is_mobile or is_tablet or is_bot),
            'is_touch_capable': is_touch_capable,
            'is_bot': is_bot,
            'raw_string': user_agent_string
        }

    except Exception as e:
        logger.warning(f"Failed to parse user agent '{user_agent_string}': {e}")
        return get_default_ua_info(user_agent_string)


def get_default_ua_info(user_agent_string=''):
    """Return default user agent info for unknown/missing agents"""
    return {
        'browser_family': 'Other',
        'browser_version': 'Unknown',
        'browser_major': None,
        'browser_minor': None,
        'os_family': 'Other',
        'os_version': 'Unknown',
        'os_major': None,
        'os_minor': None,
        'device_family': 'Other',
        'device_brand': None,
        'device_model': None,
        'is_mobile': False,
        'is_tablet': False,
        'is_pc': True,
        'is_touch_capable': False,
        'is_bot': False,
        'raw_string': user_agent_string
    }


def get_client_ip(request):
    """Get real client IP address"""
    # Check for IP in X-Forwarded-For header (load balancer/proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    # Check for IP in X-Real-IP header (Nginx)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    # Fall back to REMOTE_ADDR
    return request.META.get('REMOTE_ADDR', 'Unknown')


def get_enhanced_client_info(request):
    """
    Get comprehensive client information including modern client hints
    """
    headers = request.META
    user_agent_string = headers.get('HTTP_USER_AGENT', '')

    # Parse traditional user agent
    ua_info = parse_user_agent(user_agent_string)

    # Add client hints if available (modern browsers)
    client_hints = {
        'sec_ch_ua': headers.get('HTTP_SEC_CH_UA', ''),
        'sec_ch_ua_mobile': headers.get('HTTP_SEC_CH_UA_MOBILE', ''),
        'sec_ch_ua_platform': headers.get('HTTP_SEC_CH_UA_PLATFORM', '').strip('"'),
        'sec_ch_ua_platform_version': headers.get('HTTP_SEC_CH_UA_PLATFORM_VERSION', '').strip('"'),
        'sec_ch_ua_arch': headers.get('HTTP_SEC_CH_UA_ARCH', '').strip('"'),
        'sec_ch_ua_model': headers.get('HTTP_SEC_CH_UA_MODEL', '').strip('"'),
        'sec_ch_ua_bitness': headers.get('HTTP_SEC_CH_UA_BITNESS', '').strip('"'),
        'sec_ch_ua_full_version': headers.get('HTTP_SEC_CH_UA_FULL_VERSION', '').strip('"'),
    }

    # Enhance UA info with client hints where available
    if client_hints['sec_ch_ua_platform']:
        ua_info['os_family'] = client_hints['sec_ch_ua_platform']

    if client_hints['sec_ch_ua_platform_version']:
        ua_info['os_version'] = client_hints['sec_ch_ua_platform_version']

    if client_hints['sec_ch_ua_mobile']:
        ua_info['is_mobile'] = client_hints['sec_ch_ua_mobile'] == '?1'

    if client_hints['sec_ch_ua_model']:
        ua_info['device_model'] = client_hints['sec_ch_ua_model']

    if client_hints['sec_ch_ua_full_version']:
        ua_info['browser_version'] = client_hints['sec_ch_ua_full_version']

    # Add additional request info
    ua_info.update({
        'ip_address': get_client_ip(request),
        'accept_language': headers.get('HTTP_ACCEPT_LANGUAGE', '').split(',')[0] if headers.get(
            'HTTP_ACCEPT_LANGUAGE') else 'Unknown',
        'accept_encoding': headers.get('HTTP_ACCEPT_ENCODING', ''),
        'accept': headers.get('HTTP_ACCEPT', ''),
        'dnt': headers.get('HTTP_DNT') == '1',
        'client_hints_available': bool(client_hints['sec_ch_ua']),
        'supports_webp': 'image/webp' in headers.get('HTTP_ACCEPT', ''),
        'supports_avif': 'image/avif' in headers.get('HTTP_ACCEPT', ''),
    })

    return ua_info


def is_suspicious_request(ua_info, request):
    """
    Check if the request appears suspicious
    """
    suspicious_indicators = []

    # Check for bot-like behavior
    if ua_info['is_bot']:
        suspicious_indicators.append('detected_bot')

    # Check for missing or minimal user agent
    if not ua_info['raw_string'] or len(ua_info['raw_string']) < 10:
        suspicious_indicators.append('minimal_user_agent')

    # Check for outdated browsers (security risk)
    if ua_info['browser_family'] == 'Internet Explorer':
        suspicious_indicators.append('outdated_browser')

    # Check for programmatic access patterns
    if ua_info['browser_family'] in ['Other', 'Unknown']:
        suspicious_indicators.append('unknown_browser')

    # Check rate limiting headers or patterns
    if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
        suspicious_indicators.append('no_accept_language')

    # Check for headless browser indicators
    ua_lower = ua_info['raw_string'].lower()
    headless_indicators = ['headless', 'phantom', 'selenium', 'webdriver']
    if any(indicator in ua_lower for indicator in headless_indicators):
        suspicious_indicators.append('headless_browser')

    return {
        'is_suspicious': len(suspicious_indicators) > 0,
        'risk_score': len(suspicious_indicators),
        'indicators': suspicious_indicators
    }


# Caching for performance optimization
from django.core.cache import cache
import hashlib


def get_cached_user_agent_info(user_agent_string):
    """
    Cache parsed user agent data to improve performance
    """
    if not user_agent_string:
        return get_default_ua_info()

    # Create cache key from user agent hash
    cache_key = f"ua_parsed_{hashlib.md5(user_agent_string.encode()).hexdigest()[:16]}"

    # Try to get from cache first
    cached_info = cache.get(cache_key)
    if cached_info:
        return cached_info

    # Parse and cache for 6 hours
    ua_info = parse_user_agent(user_agent_string)
    cache.set(cache_key, ua_info, 21600)  # 6 hours

    return ua_info


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_file(request, token):
    """
    Secure file download with ua-parser user agent detection
    """
    from accounts.models import DownloadLog
    from orders.models import OrderItem

    download_start_time = time.time()

    # Get comprehensive client information
    client_info = get_enhanced_client_info(request)

    # Check for suspicious activity
    security_check = is_suspicious_request(client_info, request)

    try:
        # Find the order item with this token
        order_item = get_object_or_404(
            OrderItem,
            download_token=token,
            order__user=request.user,
            order__status='paid'
        )

        # Check if download is still valid
        if not order_item.can_download():
            # Log failed download attempt
            DownloadLog.objects.create(
                user=request.user,
                order_item=order_item,
                ip_address=client_info['ip_address'],
                user_agent=client_info['raw_string'][:1000],  # Truncate if too long
                browser_family=client_info['browser_family'][:100],
                browser_version=client_info['browser_version'][:50],
                os_family=client_info['os_family'][:100],
                os_version=client_info['os_version'][:50],
                device_family=client_info['device_family'][:100],
                device_brand=client_info['device_brand'][:100] if client_info['device_brand'] else 'Unknown',
                device_model=client_info['device_model'][:100] if client_info['device_model'] else 'Unknown',
                is_mobile=client_info['is_mobile'],
                is_tablet=client_info['is_tablet'],
                is_bot=client_info['is_bot'],
                is_suspicious=security_check['is_suspicious'],
                download_status='limit_exceeded' if order_item.download_count >= order_item.download_limit else 'expired',
                error_message='Download limit exceeded' if order_item.download_count >= order_item.download_limit else 'Download link expired'
            )
            return Response(
                {'error': 'Download link has expired or exceeded limit'},
                status=status.HTTP_410_GONE
            )

        # Additional security check for suspicious requests
        if security_check['risk_score'] > 2:
            logger.warning(
                f"Suspicious download attempt from {client_info['ip_address']}: {security_check['indicators']}")
            # You might want to require additional verification here

        # Get the file
        file_path = order_item.product.main_file.path

        if not os.path.exists(file_path):
            DownloadLog.objects.create(
                user=request.user,
                order_item=order_item,
                ip_address=client_info['ip_address'],
                user_agent=client_info['raw_string'][:1000],
                browser_family=client_info['browser_family'][:100],
                browser_version=client_info['browser_version'][:50],
                os_family=client_info['os_family'][:100],
                os_version=client_info['os_version'][:50],
                device_family=client_info['device_family'][:100],
                device_brand=client_info['device_brand'][:100] if client_info['device_brand'] else 'Unknown',
                device_model=client_info['device_model'][:100] if client_info['device_model'] else 'Unknown',
                is_mobile=client_info['is_mobile'],
                is_tablet=client_info['is_tablet'],
                is_bot=client_info['is_bot'],
                is_suspicious=security_check['is_suspicious'],
                download_status='failed',
                error_message='File not found on server'
            )
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Increment download count
        order_item.increment_download()

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        file_size = os.path.getsize(file_path)

        # Create response with appropriate headers
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type)

            # Safe filename handling
            safe_filename = "".join(c for c in order_item.product.title if c.isalnum() or c in (' ', '-', '_')).strip()
            file_extension = file_path.split('.')[-1] if '.' in file_path else 'file'

            response['Content-Disposition'] = f'attachment; filename="{safe_filename}.{file_extension}"'
            response['Content-Length'] = file_size

            # Security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['Referrer-Policy'] = 'no-referrer'
            response['X-Download-Options'] = 'noopen'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

            # Log successful download
            download_duration = time.time() - download_start_time
            DownloadLog.objects.create(
                user=request.user,
                order_item=order_item,
                ip_address=client_info['ip_address'],
                user_agent=client_info['raw_string'][:1000],
                browser_family=client_info['browser_family'][:100],
                browser_version=client_info['browser_version'][:50],
                os_family=client_info['os_family'][:100],
                os_version=client_info['os_version'][:50],
                device_family=client_info['device_family'][:100],
                device_brand=client_info['device_brand'][:100] if client_info['device_brand'] else 'Unknown',
                device_model=client_info['device_model'][:100] if client_info['device_model'] else 'Unknown',
                is_mobile=client_info['is_mobile'],
                is_tablet=client_info['is_tablet'],
                is_bot=client_info['is_bot'],
                is_suspicious=security_check['is_suspicious'],
                download_status='success',
                file_size=file_size,
                download_duration=download_duration
            )

            return response

    except OrderItem.DoesNotExist:
        return Response(
            {'error': 'Invalid download link'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error downloading file with token {token}: {e}")
        return Response(
            {'error': 'Download failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
