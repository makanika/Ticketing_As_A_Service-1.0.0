from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def custom_logout(request):
    """Custom logout view with proper message"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('account_login')