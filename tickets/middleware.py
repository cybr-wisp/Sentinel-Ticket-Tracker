
# Imports: 
import redis
from django.http import JsonResponse
import logging


logger = logging.getLogger(__name__)

# Connect to Redis - opens up a TCP connection 
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0
)

class RateLimitMiddleware:
    # runs once at server startup - not per request
    def __init__(self, get_response):
        self.get_response = get_response

    # runs per request - instance behaves like a function
    def __call__(self, request):
        protected_paths = ['/api-auth/login/', '/o/token/']

        # Only credential SUBMISSIONS are brute-force attempts — GETs just render forms
        if request.path in protected_paths and request.method == "POST":
            ip = request.META.get('REMOTE_ADDR')
            key = f"rate_limit:{ip}:{request.path}"

            try:
                count = redis_client.incr(key)
                # nx=True: set TTL only if the key has none — unconditional call
                # closes the incr/expire crash race and self-heals lost TTLs
                redis_client.expire(key, 60, nx=True)
            except redis.ConnectionError:
                # Fail open: rate limiting is defense-in-depth, not the primary
                # control. Availability of auth > this protection. Log it so the
                # degradation is visible, then let the request through.
                logger.warning(
                    "Redis unreachable — rate limiting disabled for this request"
                )
                return self.get_response(request)

            if count > 5:
                return JsonResponse({'detail': 'Too many requests'}, status=429)

        return self.get_response(request)