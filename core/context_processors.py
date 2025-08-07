
from django.conf import settings

def auth_enabled(request):
    return {'user_o365_auth_enabled': getattr(settings, 'USER_O365_AUTH_ENABLED', False)}
