from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from .models import (
    Ticket, TicketComment, TicketAttachment, TicketHistory,
    TicketCategory, Asset, User, SLA
)
from .forms import (
    TicketForm, TicketUpdateForm, TicketCommentForm, 
    TicketAttachmentForm, TicketSearchForm, BulkActionForm
)

class DashboardView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/dashboard.html'
    context_object_name = 'recent_tickets'
    paginate_by = 10
    
    def get_queryset(self):
        # Show recent tickets for the user
        if self.request.user.role in ['manager', 'admin']:
            return Ticket.objects.all()[:10]
        else:
            return Ticket.objects.filter(
                Q(assigned_to=self.request.user) | Q(created_by=self.request.user)
            )[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dashboard statistics
        if self.request.user.role in ['manager', 'admin']:
            all_tickets = Ticket.objects.all()
        else:
            all_tickets = Ticket.objects.filter(
                Q(assigned_to=self.request.user) | Q(created_by=self.request.user)
            )
        
        total_count = all_tickets.count()
        
        # Calculate priority stats with percentages
        priority_stats = {
            'p1': all_tickets.filter(priority='p1').count(),
            'p2': all_tickets.filter(priority='p2').count(),
            'p3': all_tickets.filter(priority='p3').count(),
            'p4': all_tickets.filter(priority='p4').count(),
        }
        
        # Add percentage calculations
        priority_percentages = {}
        for key, value in priority_stats.items():
            priority_percentages[key] = round((value * 100 / total_count) if total_count > 0 else 0, 1)
        
        # Calculate status stats with percentages
        status_stats = {
            'open': all_tickets.filter(status='open').count(),
            'in_progress': all_tickets.filter(status='in_progress').count(),
            'pending': all_tickets.filter(status='pending').count(),
            'resolved': all_tickets.filter(status='resolved').count(),
            'closed': all_tickets.filter(status='closed').count(),
        }
        
        # Add percentage calculations for status
        status_percentages = {}
        for key, value in status_stats.items():
            status_percentages[key] = round((value * 100 / total_count) if total_count > 0 else 0, 1)
        
        context.update({
            'total_tickets': total_count,
            'open_tickets': all_tickets.filter(status='open').count(),
            'in_progress_tickets': all_tickets.filter(status='in_progress').count(),
            'overdue_tickets': len([t for t in all_tickets if t.is_overdue]),
            'my_tickets': all_tickets.filter(assigned_to=self.request.user).count(),
            'priority_stats': priority_stats,
            'priority_percentages': priority_percentages,
            'status_stats': status_stats,
            'status_percentages': status_percentages,
        })
        
        return context

# Keep the old HomeView for backward compatibility
class HomeView(DashboardView):
    template_name = 'tickets/home.html'

class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            'category', 'subcategory', 'asset', 'assigned_to', 'created_by'
        )
        
        # Apply search filters
        form = TicketSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(ticket_id__icontains=search)
                )
            
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            priority = form.cleaned_data.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)
            
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            assigned_to = form.cleaned_data.get('assigned_to')
            if assigned_to:
                queryset = queryset.filter(assigned_to=assigned_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TicketSearchForm(self.request.GET)
        context['bulk_form'] = BulkActionForm()
        return context

class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = TicketCommentForm()
        context['attachment_form'] = TicketAttachmentForm()
        context['comments'] = self.object.comments.all()
        context['attachments'] = self.object.attachments.all()
        context['history'] = self.object.history.all()[:20]
        return context

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Auto-assign SLA based on priority
        if form.instance.priority and not form.instance.sla:
            try:
                sla = SLA.objects.filter(
                    priority=form.instance.priority, 
                    is_active=True
                ).first()
                if sla:
                    form.instance.sla = sla
            except SLA.DoesNotExist:
                pass
        
        response = super().form_valid(form)
        
        # Create history entry
        TicketHistory.objects.create(
            ticket=self.object,
            action='created',
            description=f'Ticket created by {self.request.user}',
            user=self.request.user
        )
        
        messages.success(self.request, f'Ticket {self.object.ticket_id} created successfully!')
        return response

class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Ticket
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_form.html'
    
    def form_valid(self, form):
        # Track changes for history
        old_ticket = Ticket.objects.get(pk=self.object.pk)
        changes = []
        
        for field in ['status', 'priority', 'assigned_to', 'category']:
            old_value = getattr(old_ticket, field)
            new_value = getattr(form.instance, field)
            if old_value != new_value:
                changes.append(f'{field.replace("_", " ").title()}: {old_value} → {new_value}')
        
        response = super().form_valid(form)
        
        # Create history entries for changes
        if changes:
            TicketHistory.objects.create(
                ticket=self.object,
                action='updated',
                description=f'Ticket updated: {", ".join(changes)}',
                user=self.request.user
            )
        
        messages.success(self.request, 'Ticket updated successfully!')
        return response

@login_required
def add_comment(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        form = TicketCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()
            
            # Create history entry
            TicketHistory.objects.create(
                ticket=ticket,
                action='comment_added',
                description=f'Comment added by {request.user}',
                user=request.user
            )
            
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Error adding comment. Please check your input.')
    
    return redirect('tickets:detail', pk=ticket_id)

@login_required
def add_attachment(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        form = TicketAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.ticket = ticket
            attachment.uploaded_by = request.user
            attachment.content_type = attachment.file.content_type
            attachment.save()
            
            # Create history entry
            TicketHistory.objects.create(
                ticket=ticket,
                action='attachment_added',
                description=f'Attachment "{attachment.filename}" added by {request.user}',
                user=request.user
            )
            
            messages.success(request, 'Attachment uploaded successfully!')
        else:
            messages.error(request, 'Error uploading attachment. Please check the file.')
    
    return redirect('tickets:detail', pk=ticket_id)

@login_required
def bulk_action(request):
    if request.method == 'POST':
        form = BulkActionForm(request.POST)
        ticket_ids = request.POST.getlist('selected_tickets')
        
        if form.is_valid() and ticket_ids:
            action = form.cleaned_data['action']
            tickets = Ticket.objects.filter(id__in=ticket_ids)
            
            if action == 'assign':
                assigned_to = form.cleaned_data['assigned_to']
                if assigned_to:
                    tickets.update(assigned_to=assigned_to)
                    messages.success(request, f'{len(ticket_ids)} tickets assigned to {assigned_to}')
            
            elif action == 'status':
                status = form.cleaned_data['status']
                if status:
                    tickets.update(status=status)
                    messages.success(request, f'{len(ticket_ids)} tickets status changed to {status}')
            
            elif action == 'priority':
                priority = form.cleaned_data['priority']
                if priority:
                    tickets.update(priority=priority)
                    messages.success(request, f'{len(ticket_ids)} tickets priority changed to {priority}')
            
            elif action == 'close':
                tickets.update(status='closed', closed_at=timezone.now())
                messages.success(request, f'{len(ticket_ids)} tickets closed')
        
        else:
            messages.error(request, 'Please select tickets and a valid action')
    
    return redirect('tickets:list')

@login_required
def ticket_stats_api(request):
    """API endpoint for dashboard charts"""
    # Get date range (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Tickets created per day
    daily_tickets = []
    current_date = start_date
    while current_date <= end_date:
        count = Ticket.objects.filter(created_at__date=current_date).count()
        daily_tickets.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count
        })
        current_date += timedelta(days=1)
    
    # Priority distribution
    priority_data = []
    for priority, label in Ticket.PRIORITY_CHOICES:
        count = Ticket.objects.filter(priority=priority).count()
        priority_data.append({
            'priority': label,
            'count': count
        })
    
    # Status distribution
    status_data = []
    for status, label in Ticket.STATUS_CHOICES:
        count = Ticket.objects.filter(status=status).count()
        status_data.append({
            'status': label,
            'count': count
        })
    
    return JsonResponse({
        'daily_tickets': daily_tickets,
        'priority_distribution': priority_data,
        'status_distribution': status_data
    })

@login_required
def reports_view(request):
    """Reports and analytics page"""
    total_tickets = Ticket.objects.count()
    
    # Get categories with ticket counts and calculate percentages
    categories = TicketCategory.objects.annotate(
        ticket_count=Count('ticket')
    ).order_by('-ticket_count')
    
    # Add percentage calculation for categories
    categories_with_percentages = []
    for category in categories:
        percentage = round((category.ticket_count * 100 / total_tickets) if total_tickets > 0 else 0, 1)
        categories_with_percentages.append({
            'category': category,
            'percentage': percentage
        })
    
    # Get top assignees with ticket counts and calculate percentages
    top_assignees = User.objects.annotate(
        ticket_count=Count('assigned_tickets')
    ).order_by('-ticket_count')[:10]
    
    # Add percentage calculation for assignees
    assignees_with_percentages = []
    for assignee in top_assignees:
        percentage = round((assignee.ticket_count * 100 / total_tickets) if total_tickets > 0 else 0, 1)
        assignees_with_percentages.append({
            'assignee': assignee,
            'percentage': percentage
        })
    
    # Calculate average resolution time manually (SQLite doesn't support Avg on datetime)
    resolved_tickets = Ticket.objects.filter(resolved_at__isnull=False)
    avg_resolution_time = None
    
    if resolved_tickets.exists():
        total_resolution_time = timedelta(0)
        count = 0
        
        for ticket in resolved_tickets:
            if ticket.resolved_at and ticket.created_at:
                resolution_time = ticket.resolved_at - ticket.created_at
                total_resolution_time += resolution_time
                count += 1
        
        if count > 0:
            avg_resolution_time = total_resolution_time / count
    
    context = {
        'total_tickets': total_tickets,
        'avg_resolution_time': avg_resolution_time,
        'categories': categories,
        'categories_with_percentages': categories_with_percentages,
        'top_assignees': top_assignees,
        'assignees_with_percentages': assignees_with_percentages,
    }
    
    return render(request, 'tickets/reports.html', context)