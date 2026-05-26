from django.core.cache import cache
from django.http import HttpResponse

HttpResponseTooManyRequests = lambda msg: HttpResponse(msg, status=429)
import time

def rate_limit(key_prefix, max_requests=5, window=300):
    """Limit requests to max_requests per window (seconds)."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'anonymous')
            cache_key = f"rate_limit:{key_prefix}:{user_id}"
            
            requests = cache.get(cache_key, [])
            now = time.time()
            requests = [t for t in requests if now - t < window]
            
            if len(requests) >= max_requests:
                return HttpResponseTooManyRequests("Rate limit exceeded. Try again later.")
            
            requests.append(now)
            cache.set(cache_key, requests, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
