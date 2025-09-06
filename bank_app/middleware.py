# bank_app/middleware.py
from datetime import timedelta
from django.utils import timezone

class SessionTimeoutMiddleware:
    """
    Sets session expiry dynamically:
    - Admins: 1 minute
    - Regular users: 10 minutes
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                # Admins: 1 minute timeout
                request.session.set_expiry(60)
            else:
                # Regular users: 10 minutes timeout
                request.session.set_expiry(60)

        response = self.get_response(request)
        return response
