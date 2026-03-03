import logging
import time

logger = logging.getLogger("core")


class RequestLoggingMiddleware:
    """Log every API request: method, path, status_code, duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "%s %s %s %dms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
