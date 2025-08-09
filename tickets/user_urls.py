from django.urls import path
from .user_views import (
    UserRegistrationView, UserProfileView, UserUpdateView, UserListView,
    change_password, user_activity, user_stats_api, toggle_user_status,
    AdminUserCreateView
)
from .auth_views import custom_logout

app_name = 'users'

urlpatterns = [
    # Registration
    path('register/', UserRegistrationView.as_view(), name='register'),
    
    # Profile management
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/<int:pk>/', UserProfileView.as_view(), name='profile_detail'),
    path('profile/<int:pk>/edit/', UserUpdateView.as_view(), name='edit_profile'),
    path('profile/edit/', UserUpdateView.as_view(), name='edit_my_profile'),
    
    # Password management
    path('password/change/', change_password, name='change_password'),
    
    # Authentication
    path('logout/', custom_logout, name='logout'),
    
    # User activity
    path('activity/', user_activity, name='activity'),
    path('activity/<int:pk>/', user_activity, name='user_activity'),
    
    # User management (staff only)
    path('list/', UserListView.as_view(), name='list'),
    path('create/', AdminUserCreateView.as_view(), name='admin_create'),
    path('<int:pk>/toggle-status/', toggle_user_status, name='toggle_status'),
    
    # API endpoints
    path('api/stats/', user_stats_api, name='stats_api'),
    path('api/stats/<int:pk>/', user_stats_api, name='user_stats_api'),
]