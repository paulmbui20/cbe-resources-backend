from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
import redis
from django.conf import settings

@login_not_required
def health_check(request):
    """
    Health check endpoint for Docker containers
    """
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'cache': 'unknown',
        'redis': 'unknown'
    }

    # Check database connection
    try:
        db_conn = connections['default']
        db_conn.cursor()
        health_status['database'] = 'healthy'
    except Exception as e:
        health_status['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Check cache (Django cache)
    try:
        cache.set('health_check', 'test', 30)
        if cache.get('health_check') == 'test':
            health_status['cache'] = 'healthy'
        else:
            health_status['cache'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Check Redis connection
    try:
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        health_status['redis'] = 'healthy'
    except Exception as e:
        health_status['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
