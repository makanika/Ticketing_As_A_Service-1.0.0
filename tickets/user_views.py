from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from .models import User, Ticket, TicketHistory
from .forms import CustomUserCreationForm, UserProfileForm, UserUpdateForm

class UserRegistrationView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            'Account created successfully! You can now log in.'
        )
        return response
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users away from registration
        if request.user.is_authenticated:
            return redirect('tickets:dashboard')
        return super().dispatch(request, *args, **kwargs)

class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        # Allow users to view their own profile or any profile if they're staff
        user_id = self.kwargs.get('pk')
        if user_id:
            if self.request.user.is_staff or str(self.request.user.pk) == str(user_id):
                return get_object_or_404(User, pk=user_id)
            else:
                # Non-staff users can only view their own profile
                return self.request.user
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Get user's ticket statistics
        created_tickets = Ticket.objects.filter(created_by=user)
        assigned_tickets = Ticket.objects.filter(assigned_to=user)
        
        # Recent activity
        recent_created = created_tickets.order_by('-created_at')[:5]
        recent_assigned = assigned_tickets.order_by('-created_at')[:5]
        
        # Statistics
        context.update({
            'total_created': created_tickets.count(),
            'total_assigned': assigned_tickets.count(),
            'open_assigned': assigned_tickets.filter(status='open').count(),
            'in_progress_assigned': assigned_tickets.filter(status='in_progress').count(),
            'resolved_assigned': assigned_tickets.filter(status='resolved').count(),
            'recent_created': recent_created,
            'recent_assigned': recent_assigned,
            'can_edit': self.request.user == user or self.request.user.is_staff,
        })
        
        return context

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/edit_profile.html'
    
    def get_object(self):
        # Users can only edit their own profile unless they're staff
        user_id = self.kwargs.get('pk')
        if user_id and (self.request.user.is_staff or str(self.request.user.pk) == str(user_id)):
            return get_object_or_404(User, pk=user_id)
        return self.request.user
    
    def get_success_url(self):
        # If editing someone else's profile (staff), redirect to their profile detail
        # If editing own profile, redirect to own profile
        if self.kwargs.get('pk'):
            return reverse('users:profile_detail', kwargs={'pk': self.object.pk})
        else:
            return reverse('users:profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Only staff can view user list
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to view the user list.')
            return redirect('tickets:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('last_name', 'first_name')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_choices'] = User.ROLE_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['selected_active'] = self.request.GET.get('is_active', '')
        return context

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {
        'form': form
    })

@login_required
def user_activity(request, pk=None):
    """View user activity and ticket history"""
    if pk:
        if request.user.is_staff or str(request.user.pk) == str(pk):
            user = get_object_or_404(User, pk=pk)
        else:
            user = request.user
    else:
        user = request.user
    
    # Get user's ticket activity
    created_tickets = Ticket.objects.filter(created_by=user).order_by('-created_at')
    assigned_tickets = Ticket.objects.filter(assigned_to=user).order_by('-updated_at')
    
    # Get user's history entries
    history_entries = TicketHistory.objects.filter(user=user).order_by('-timestamp')[:50]
    
    # Pagination
    created_paginator = Paginator(created_tickets, 10)
    assigned_paginator = Paginator(assigned_tickets, 10)
    
    created_page = request.GET.get('created_page', 1)
    assigned_page = request.GET.get('assigned_page', 1)
    
    created_tickets_page = created_paginator.get_page(created_page)
    assigned_tickets_page = assigned_paginator.get_page(assigned_page)
    
    context = {
        'profile_user': user,
        'created_tickets': created_tickets_page,
        'assigned_tickets': assigned_tickets_page,
        'history_entries': history_entries,
        'can_edit': request.user == user or request.user.is_staff,
    }
    
    return render(request, 'users/user_activity.html', context)

@login_required
def user_stats_api(request, pk=None):
    """API endpoint for user statistics"""
    if pk:
        if request.user.is_staff or str(request.user.pk) == str(pk):
            user = get_object_or_404(User, pk=pk)
        else:
            user = request.user
    else:
        user = request.user
    
    # Get date range (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Tickets created by user per day
    daily_created = []
    current_date = start_date
    while current_date <= end_date:
        count = Ticket.objects.filter(
            created_by=user,
            created_at__date=current_date
        ).count()
        daily_created.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count
        })
        current_date += timedelta(days=1)
    
    # Tickets assigned to user by status
    assigned_stats = {}
    for status, label in Ticket.STATUS_CHOICES:
        count = Ticket.objects.filter(assigned_to=user, status=status).count()
        assigned_stats[status] = {
            'label': label,
            'count': count
        }
    
    return JsonResponse({
        'daily_created': daily_created,
        'assigned_stats': assigned_stats,
        'total_created': Ticket.objects.filter(created_by=user).count(),
        'total_assigned': Ticket.objects.filter(assigned_to=user).count(),
    })

@login_required
def toggle_user_status(request, pk):
    """Toggle user active status (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('tickets:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.get_full_name()} has been {status}.')
    
    return redirect('users:list')