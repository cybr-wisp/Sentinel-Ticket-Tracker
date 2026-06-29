
# Imports: 
import redis
from django.http import JsonResponse

# Connect to Redis
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0
)

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected_paths = ['/api-auth/login/', '/o/token/']
        
        if request.path in protected_paths:
            ip = request.META.get('REMOTE_ADDR')
            key = f"rate_limit:{ip}:{request.path}"

            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, 60)

            if count > 5:
                return JsonResponse({'detail': 'Too many requests'}, status=429)

        return self.get_response(request)