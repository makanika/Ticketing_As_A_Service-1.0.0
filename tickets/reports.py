import csv
import json
from datetime import datetime, timedelta
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import HexColor

from .models import Ticket, TicketCategory, User, Asset, SLA, TicketHistory

@login_required
def reports_dashboard(request):
    """Enhanced reports dashboard with filtering options"""
    # Get date range from request or default to last 30 days
    end_date = request.GET.get('end_date')
    start_date = request.GET.get('start_date')
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=30)
    
    # Filter tickets by date range
    tickets_queryset = Ticket.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Basic statistics
    total_tickets = tickets_queryset.count()
    open_tickets = tickets_queryset.filter(status='open').count()
    closed_tickets = tickets_queryset.filter(status='closed').count()
    resolved_tickets = tickets_queryset.filter(status='resolved').count()
    
    # Priority distribution
    priority_stats = {
        'p1': tickets_queryset.filter(priority='p1').count(),
        'p2': tickets_queryset.filter(priority='p2').count(),
        'p3': tickets_queryset.filter(priority='p3').count(),
        'p4': tickets_queryset.filter(priority='p4').count(),
    }
    
    # Status distribution
    status_stats = {
        'open': open_tickets,
        'in_progress': tickets_queryset.filter(status='in_progress').count(),
        'pending': tickets_queryset.filter(status='pending').count(),
        'resolved': resolved_tickets,
        'closed': closed_tickets,
        'cancelled': tickets_queryset.filter(status='cancelled').count(),
    }
    
    # Category analysis
    categories = TicketCategory.objects.annotate(
        ticket_count=Count('ticket', filter=Q(
            ticket__created_at__date__gte=start_date,
            ticket__created_at__date__lte=end_date
        ))
    ).order_by('-ticket_count')
    
    # Top assignees
    top_assignees = User.objects.annotate(
        ticket_count=Count('assigned_tickets', filter=Q(
            assigned_tickets__created_at__date__gte=start_date,
            assigned_tickets__created_at__date__lte=end_date
        ))
    ).filter(ticket_count__gt=0).order_by('-ticket_count')[:10]
    
    # SLA performance
    sla_performance = []
    for sla in SLA.objects.filter(is_active=True):
        sla_tickets = tickets_queryset.filter(sla=sla)
        total_sla_tickets = sla_tickets.count()
        
        if total_sla_tickets > 0:
            # Calculate SLA compliance
            compliant_tickets = 0
            for ticket in sla_tickets:
                if ticket.resolved_at:
                    resolution_time = ticket.resolved_at - ticket.created_at
                    if resolution_time.total_seconds() <= sla.resolution_time_hours * 3600:
                        compliant_tickets += 1
            
            compliance_rate = (compliant_tickets / total_sla_tickets) * 100
            sla_performance.append({
                'sla': sla,
                'total_tickets': total_sla_tickets,
                'compliant_tickets': compliant_tickets,
                'compliance_rate': round(compliance_rate, 1)
            })
    
    # Daily ticket creation trend
    daily_trends = []
    current_date = start_date
    while current_date <= end_date:
        daily_count = tickets_queryset.filter(created_at__date=current_date).count()
        daily_trends.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': daily_count
        })
        current_date += timedelta(days=1)
    
    # Average resolution time
    resolved_tickets_with_time = tickets_queryset.filter(
        resolved_at__isnull=False
    )
    
    avg_resolution_time = None
    if resolved_tickets_with_time.exists():
        total_resolution_time = timedelta(0)
        count = 0
        
        for ticket in resolved_tickets_with_time:
            if ticket.resolved_at and ticket.created_at:
                resolution_time = ticket.resolved_at - ticket.created_at
                total_resolution_time += resolution_time
                count += 1
        
        if count > 0:
            avg_resolution_time = total_resolution_time / count
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'closed_tickets': closed_tickets,
        'resolved_tickets': resolved_tickets,
        'priority_stats': priority_stats,
        'status_stats': status_stats,
        'categories': categories,
        'top_assignees': top_assignees,
        'sla_performance': sla_performance,
        'daily_trends': daily_trends,
        'avg_resolution_time': avg_resolution_time,
    }
    
    return render(request, 'tickets/reports_dashboard.html', context)

@login_required
def export_tickets_csv(request):
    """Export tickets data to CSV"""
    # Get date range and filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    
    # Build queryset
    queryset = Ticket.objects.select_related(
        'category', 'subcategory', 'asset', 'assigned_to', 'created_by', 'sla'
    )
    
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__gte=start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__lte=end_date_obj)
    
    if status:
        queryset = queryset.filter(status=status)
    
    if priority:
        queryset = queryset.filter(priority=priority)
    
    if category:
        queryset = queryset.filter(category_id=category)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tickets_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Ticket ID', 'Title', 'Description', 'Status', 'Priority', 'Category',
        'Subcategory', 'Asset', 'Created By', 'Assigned To', 'Created At',
        'Updated At', 'Resolved At', 'Closed At', 'SLA', 'Contact Name',
        'Contact Email', 'Contact Phone', 'Estimated Hours', 'Actual Hours'
    ])
    
    # Write data
    for ticket in queryset.order_by('-created_at'):
        writer.writerow([
            ticket.ticket_id,
            ticket.title,
            ticket.description,
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.category.name if ticket.category else '',
            ticket.subcategory.name if ticket.subcategory else '',
            ticket.asset.name if ticket.asset else '',
            ticket.created_by.get_full_name(),
            ticket.assigned_to.get_full_name() if ticket.assigned_to else '',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            ticket.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.resolved_at else '',
            ticket.closed_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.closed_at else '',
            ticket.sla.name if ticket.sla else '',
            ticket.contact_name or '',
            ticket.contact_email or '',
            ticket.contact_phone or '',
            ticket.estimated_hours or '',
            ticket.actual_hours or '',
        ])
    
    return response

@login_required
def export_tickets_json(request):
    """Export tickets data to JSON"""
    # Get date range and filters (same as CSV)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    
    # Build queryset
    queryset = Ticket.objects.select_related(
        'category', 'subcategory', 'asset', 'assigned_to', 'created_by', 'sla'
    )
    
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__gte=start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__lte=end_date_obj)
    
    if status:
        queryset = queryset.filter(status=status)
    
    if priority:
        queryset = queryset.filter(priority=priority)
    
    if category:
        queryset = queryset.filter(category_id=category)
    
    # Build data structure
    tickets_data = []
    for ticket in queryset.order_by('-created_at'):
        ticket_data = {
            'ticket_id': ticket.ticket_id,
            'title': ticket.title,
            'description': ticket.description,
            'status': ticket.status,
            'status_display': ticket.get_status_display(),
            'priority': ticket.priority,
            'priority_display': ticket.get_priority_display(),
            'category': {
                'id': ticket.category.id if ticket.category else None,
                'name': ticket.category.name if ticket.category else None
            },
            'subcategory': {
                'id': ticket.subcategory.id if ticket.subcategory else None,
                'name': ticket.subcategory.name if ticket.subcategory else None
            },
            'asset': {
                'id': ticket.asset.id if ticket.asset else None,
                'name': ticket.asset.name if ticket.asset else None
            },
            'created_by': {
                'id': ticket.created_by.id,
                'username': ticket.created_by.username,
                'full_name': ticket.created_by.get_full_name()
            },
            'assigned_to': {
                'id': ticket.assigned_to.id if ticket.assigned_to else None,
                'username': ticket.assigned_to.username if ticket.assigned_to else None,
                'full_name': ticket.assigned_to.get_full_name() if ticket.assigned_to else None
            },
            'sla': {
                'id': ticket.sla.id if ticket.sla else None,
                'name': ticket.sla.name if ticket.sla else None
            },
            'contact': {
                'name': ticket.contact_name or '',
                'email': ticket.contact_email or '',
                'phone': ticket.contact_phone or ''
            },
            'hours': {
                'estimated': float(ticket.estimated_hours) if ticket.estimated_hours else None,
                'actual': float(ticket.actual_hours) if ticket.actual_hours else None
            },
            'timestamps': {
                'created_at': ticket.created_at.isoformat(),
                'updated_at': ticket.updated_at.isoformat(),
                'resolved_at': ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                'closed_at': ticket.closed_at.isoformat() if ticket.closed_at else None
            }
        }
        tickets_data.append(ticket_data)
    
    # Create response
    response_data = {
        'export_timestamp': timezone.now().isoformat(),
        'total_tickets': len(tickets_data),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'priority': priority,
            'category': category
        },
        'tickets': tickets_data
    }
    
    response = HttpResponse(
        json.dumps(response_data, cls=DjangoJSONEncoder, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="tickets_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response

@login_required
def export_tickets_pdf(request):
    """Export tickets data to PDF"""
    # Get date range and filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    
    # Build queryset
    queryset = Ticket.objects.select_related(
        'category', 'subcategory', 'asset', 'assigned_to', 'created_by', 'sla'
    )
    
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__gte=start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        queryset = queryset.filter(created_at__date__lte=end_date_obj)
    
    if status:
        queryset = queryset.filter(status=status)
    
    if priority:
        queryset = queryset.filter(priority=priority)
    
    if category:
        queryset = queryset.filter(category_id=category)
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph('Tickets Report', title_style))
    content.append(Spacer(1, 12))
    
    # Report info
    report_info = f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
    if start_date:
        report_info += f"Start Date: {start_date}<br/>"
    if end_date:
        report_info += f"End Date: {end_date}<br/>"
    if status:
        report_info += f"Status Filter: {status}<br/>"
    if priority:
        report_info += f"Priority Filter: {priority}<br/>"
    
    content.append(Paragraph(report_info, styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Summary statistics
    total_tickets = queryset.count()
    content.append(Paragraph(f'Total Tickets: {total_tickets}', styles['Heading2']))
    content.append(Spacer(1, 12))
    
    # Tickets table
    if total_tickets > 0:
        # Table headers
        table_data = [[
            'Ticket ID', 'Title', 'Status', 'Priority', 'Category',
            'Assigned To', 'Created At'
        ]]
        
        # Table data
        for ticket in queryset.order_by('-created_at')[:100]:  # Limit to 100 for PDF
            table_data.append([
                ticket.ticket_id,
                ticket.title[:30] + '...' if len(ticket.title) > 30 else ticket.title,
                ticket.get_status_display(),
                ticket.get_priority_display(),
                ticket.category.name if ticket.category else 'N/A',
                ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned',
                ticket.created_at.strftime('%Y-%m-%d')
            ])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        
        if total_tickets > 100:
            content.append(Spacer(1, 12))
            content.append(Paragraph(f'Note: Only first 100 tickets shown. Total: {total_tickets}', styles['Italic']))
    
    # Build PDF
    doc.build(content)
    
    # Return response
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tickets_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def reports_api(request):
    """API endpoint for reports data"""
    # Get date range
    end_date = request.GET.get('end_date')
    start_date = request.GET.get('start_date')
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=30)
    
    # Get tickets in date range
    tickets = Ticket.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Daily trends
    daily_trends = []
    current_date = start_date
    while current_date <= end_date:
        daily_count = tickets.filter(created_at__date=current_date).count()
        daily_trends.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': daily_count
        })
        current_date += timedelta(days=1)
    
    # Priority distribution
    priority_data = []
    for priority, label in Ticket.PRIORITY_CHOICES:
        count = tickets.filter(priority=priority).count()
        priority_data.append({
            'priority': priority,
            'label': label,
            'count': count
        })
    
    # Status distribution
    status_data = []
    for status, label in Ticket.STATUS_CHOICES:
        count = tickets.filter(status=status).count()
        status_data.append({
            'status': status,
            'label': label,
            'count': count
        })
    
    # Category distribution
    category_data = []
    categories = TicketCategory.objects.annotate(
        ticket_count=Count('ticket', filter=Q(
            ticket__created_at__date__gte=start_date,
            ticket__created_at__date__lte=end_date
        ))
    ).order_by('-ticket_count')
    
    for category in categories:
        if category.ticket_count > 0:
            category_data.append({
                'category': category.name,
                'count': category.ticket_count
            })
    
    return JsonResponse({
        'daily_trends': daily_trends,
        'priority_distribution': priority_data,
        'status_distribution': status_data,
        'category_distribution': category_data,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    })