
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Asset, Ticket, TicketCategory, TicketSubcategory, 
    SLA, TicketComment, TicketAttachment, TicketHistory,
    KnowledgeBaseArticle, TicketTemplate
)

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'department')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'department')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')

@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(TicketSubcategory)
class TicketSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'category__name')

@admin.register(SLA)
class SLAAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'response_time_hours', 'resolution_time_hours', 'is_active')
    list_filter = ('priority', 'is_active')
    search_fields = ('name',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_type', 'location', 'last_maintenance_date')
    list_filter = ('asset_type', 'location')
    search_fields = ('name', 'serial_number')

class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ('created_at',)

class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_id', 'title', 'category', 'status', 'priority', 
        'assigned_to', 'created_by', 'created_at', 'is_overdue'
    )
    list_filter = (
        'status', 'priority', 'category', 'subcategory', 
        'source', 'created_at', 'assigned_to'
    )
    search_fields = ('title', 'description', 'ticket_id', 'contact_name', 'contact_email')
    raw_id_fields = ('asset', 'created_by', 'assigned_to')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at', 'first_response_at', 'resolved_at', 'closed_at')
    inlines = [TicketCommentInline, TicketAttachmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('ticket_id', 'title', 'description', 'category', 'subcategory')
        }),
        ('Assignment & Priority', {
            'fields': ('status', 'priority', 'source', 'assigned_to', 'sla')
        }),
        ('Asset & Contact', {
            'fields': ('asset', 'contact_name', 'contact_email', 'contact_phone')
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours')
        }),
        ('Resolution', {
            'fields': ('resolution_notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'first_response_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
        ('Created By', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        })
    )
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'

@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('content', 'ticket__ticket_id')
    raw_id_fields = ('ticket', 'author')

@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'ticket', 'uploaded_by', 'file_size_human', 'uploaded_at')
    list_filter = ('uploaded_at', 'content_type')
    search_fields = ('filename', 'ticket__ticket_id')
    raw_id_fields = ('ticket', 'uploaded_by')

@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'action', 'user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('ticket__ticket_id', 'description')
    raw_id_fields = ('ticket', 'user')
    readonly_fields = ('timestamp',)

@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'view_count', 'updated_at')
    list_filter = ('category', 'is_published', 'created_at')
    search_fields = ('title', 'content', 'tags')
    raw_id_fields = ('author',)
    readonly_fields = ('view_count', 'created_at', 'updated_at')

@admin.register(TicketTemplate)
class TicketTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'priority', 'is_active', 'created_by', 'created_at')
    list_filter = ('category', 'priority', 'is_active', 'created_at')
    search_fields = ('name', 'title_template')
    raw_id_fields = ('created_by',)


