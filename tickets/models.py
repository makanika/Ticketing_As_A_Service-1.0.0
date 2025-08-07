
from django.db import models, OperationalError
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import os

def get_next_ticket_id():
    try:
        last_ticket = Ticket.objects.all().order_by('id').last()
        if not last_ticket:
            return 'RX-UG-INC-000001'
        # Extract the numeric part from the ticket ID
        ticket_id_parts = last_ticket.ticket_id.split('-')
        if len(ticket_id_parts) >= 4:
            last_id = int(ticket_id_parts[-1])
            new_id = last_id + 1
            return f'RX-UG-INC-{new_id:06d}'
        else:
            return 'RX-UG-INC-000001'
    except (OperationalError, NameError, ValueError, AttributeError):
        # This can happen on the very first migration when the Ticket table doesn't exist yet.
        return 'RX-UG-INC-000001'

def ticket_attachment_path(instance, filename):
    return f'ticket_attachments/{instance.ticket.ticket_id}/{filename}'

class User(AbstractUser):
    ROLE_CHOICES = (
        ('technician', 'Facilities Technician'),
        ('engineer', 'Facilities Engineer'),
        ('manager', 'Facilities Manager'),
        ('bms', 'BMS/Control Centre Staff'),
        ('admin', 'System Administrator'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def __str__(self):
        return self.get_full_name()

class Asset(models.Model):
    ASSET_TYPES = [
        ('genset', 'Generator Set'), ('ahu', 'Air Handling Unit'),
        ('iac', 'In-Row Air Conditioner'), ('battery', 'Battery Bank'),
        ('grp_tank', 'GRP Tank'), ('pump', 'Pump'), ('ro_plant', 'RO Plant'),
        ('fire_suppression', 'Fire Suppression System'), ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
    location = models.CharField(max_length=200, help_text="e.g., Data Hall 1, Roof Level")
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    last_maintenance_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({{self.get_asset_type_display()}})"

class TicketCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Hex color code')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Ticket Categories'
    
    def __str__(self):
        return self.name

class TicketSubcategory(models.Model):
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Ticket Subcategories'
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"

class SLA(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    response_time_hours = models.PositiveIntegerField(help_text='Response time in hours')
    resolution_time_hours = models.PositiveIntegerField(help_text='Resolution time in hours')
    priority = models.CharField(max_length=10, choices=[('p1', 'P1 - Critical'), ('p2', 'P2 - High'), ('p3', 'P3 - Medium'), ('p4', 'P4 - Low')])
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_priority_display()})"

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ]
    PRIORITY_CHOICES = [('p1', 'P1 - Critical'), ('p2', 'P2 - High'), ('p3', 'P3 - Medium'), ('p4', 'P4 - Low')]
    
    SOURCE_CHOICES = [
        ('web', 'Web Portal'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('walk_in', 'Walk-in'),
        ('system', 'System Generated')
    ]

    ticket_id = models.CharField(max_length=20, unique=True, default=get_next_ticket_id)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(TicketSubcategory, on_delete=models.SET_NULL, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='p3')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='web')
    sla = models.ForeignKey(SLA, on_delete=models.SET_NULL, null=True, blank=True)
    
    # User relationships
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    resolution_notes = models.TextField(blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Contact information
    contact_name = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['created_at']),
        ]
    

    def __str__(self):
        return f"{self.ticket_id}: {self.title}"
    
    def get_absolute_url(self):
        return reverse('tickets:detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        if not self.sla or self.status in ['resolved', 'closed', 'cancelled']:
            return False
        
        if not self.first_response_at:
            # Check response time SLA
            response_deadline = self.created_at + timezone.timedelta(hours=self.sla.response_time_hours)
            if timezone.now() > response_deadline:
                return True
        
        # Check resolution time SLA
        resolution_deadline = self.created_at + timezone.timedelta(hours=self.sla.resolution_time_hours)
        return timezone.now() > resolution_deadline
    
    @property
    def time_to_resolution(self):
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None
    
    @property
    def time_to_first_response(self):
        if self.first_response_at:
            return self.first_response_at - self.created_at
        return None
    
    def save(self, *args, **kwargs):
        # Auto-set resolved_at when status changes to resolved
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        # Auto-set closed_at when status changes to closed
        if self.status == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()
        


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Internal comments are only visible to staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.ticket.ticket_id} by {self.author}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Set first_response_at if this is the first staff comment
        if is_new and not self.ticket.first_response_at and self.author.is_staff:
            self.ticket.first_response_at = self.created_at
            self.ticket.save(update_fields=['first_response_at'])

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=ticket_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.filename} - {self.ticket.ticket_id}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    @property
    def file_size_human(self):
        """Return file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"

class TicketHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'Ticket Created'),
        ('updated', 'Ticket Updated'),
        ('assigned', 'Ticket Assigned'),
        ('status_changed', 'Status Changed'),
        ('priority_changed', 'Priority Changed'),
        ('comment_added', 'Comment Added'),
        ('attachment_added', 'Attachment Added'),
        ('resolved', 'Ticket Resolved'),
        ('closed', 'Ticket Closed'),
        ('reopened', 'Ticket Reopened'),
    ]
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Ticket History'
    
    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.get_action_display()}"

class KnowledgeBaseArticle(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text='Comma-separated tags')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('tickets:kb_article', kwargs={'pk': self.pk})

class TicketTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=255)
    description_template = models.TextField()
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(TicketSubcategory, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Ticket.PRIORITY_CHOICES, default='p3')
    sla = models.ForeignKey(SLA, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
