
from django.urls import path
from .views import (
    HomeView, DashboardView, TicketListView, TicketDetailView,
    TicketCreateView, TicketUpdateView, add_comment, add_attachment,
    bulk_action, ticket_stats_api, reports_view
)

app_name = 'tickets'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('tickets/', TicketListView.as_view(), name='list'),
    path('tickets/create/', TicketCreateView.as_view(), name='create'),
    path('tickets/<int:pk>/', TicketDetailView.as_view(), name='detail'),
    path('tickets/<int:pk>/edit/', TicketUpdateView.as_view(), name='edit'),
    path('tickets/<int:ticket_id>/comment/', add_comment, name='add_comment'),
    path('tickets/<int:ticket_id>/attachment/', add_attachment, name='add_attachment'),
    path('tickets/bulk-action/', bulk_action, name='bulk_action'),
    path('api/stats/', ticket_stats_api, name='stats_api'),
    path('reports/', reports_view, name='reports'),
]
