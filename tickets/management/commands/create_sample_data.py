from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tickets.models import (
    TicketCategory, TicketSubcategory, SLA, Asset, Ticket, 
    TicketComment, TicketHistory, KnowledgeBaseArticle
)
from django.utils import timezone
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for the ticketing system'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample users
        self.create_users()
        
        # Create categories and subcategories
        self.create_categories()
        
        # Create SLAs
        self.create_slas()
        
        # Create assets
        self.create_assets()
        
        # Create tickets
        self.create_tickets()
        
        # Create knowledge base articles
        self.create_kb_articles()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def create_users(self):
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_user(
                username='admin',
                email='admin@datacenter.com',
                password='admin123',
                first_name='System',
                last_name='Administrator',
                role='admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f'Created admin user: {admin.username}')

        # Create sample staff users
        staff_users = [
            {
                'username': 'john.doe',
                'email': 'john.doe@datacenter.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'engineer',
                'department': 'Facilities Engineering'
            },
            {
                'username': 'jane.smith',
                'email': 'jane.smith@datacenter.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'technician',
                'department': 'Facilities Maintenance'
            },
            {
                'username': 'mike.wilson',
                'email': 'mike.wilson@datacenter.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'role': 'manager',
                'department': 'Facilities Management'
            },
            {
                'username': 'sarah.jones',
                'email': 'sarah.jones@datacenter.com',
                'first_name': 'Sarah',
                'last_name': 'Jones',
                'role': 'bms',
                'department': 'BMS Operations'
            }
        ]
        
        for user_data in staff_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    password='password123',
                    is_staff=True,
                    **user_data
                )
                self.stdout.write(f'Created user: {user.username}')

    def create_categories(self):
        categories_data = [
            {
                'name': 'HVAC Systems',
                'description': 'Heating, Ventilation, and Air Conditioning',
                'color': '#3B82F6',
                'subcategories': [
                    'Air Handling Unit (AHU)',
                    'In-Row Cooling',
                    'Chilled Water System',
                    'Temperature Control',
                    'Humidity Control'
                ]
            },
            {
                'name': 'Power Systems',
                'description': 'Electrical power and backup systems',
                'color': '#EF4444',
                'subcategories': [
                    'UPS Systems',
                    'Generator Sets',
                    'PDU Issues',
                    'Battery Systems',
                    'Power Quality'
                ]
            },
            {
                'name': 'Fire Safety',
                'description': 'Fire detection and suppression systems',
                'color': '#F59E0B',
                'subcategories': [
                    'Fire Suppression',
                    'Smoke Detection',
                    'Fire Alarms',
                    'Emergency Systems'
                ]
            },
            {
                'name': 'Water Systems',
                'description': 'Water supply and treatment systems',
                'color': '#10B981',
                'subcategories': [
                    'RO Plant',
                    'Water Pumps',
                    'GRP Tanks',
                    'Water Quality',
                    'Leak Detection'
                ]
            },
            {
                'name': 'Security',
                'description': 'Physical security systems',
                'color': '#8B5CF6',
                'subcategories': [
                    'Access Control',
                    'CCTV Systems',
                    'Intrusion Detection',
                    'Perimeter Security'
                ]
            }
        ]
        
        for cat_data in categories_data:
            subcategories = cat_data.pop('subcategories')
            category, created = TicketCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
            
            for subcat_name in subcategories:
                subcat, created = TicketSubcategory.objects.get_or_create(
                    category=category,
                    name=subcat_name
                )
                if created:
                    self.stdout.write(f'  Created subcategory: {subcat.name}')

    def create_slas(self):
        slas_data = [
            {
                'name': 'Critical Priority SLA',
                'description': 'For P1 critical issues',
                'response_time_hours': 1,
                'resolution_time_hours': 4,
                'priority': 'p1'
            },
            {
                'name': 'High Priority SLA',
                'description': 'For P2 high priority issues',
                'response_time_hours': 2,
                'resolution_time_hours': 8,
                'priority': 'p2'
            },
            {
                'name': 'Medium Priority SLA',
                'description': 'For P3 medium priority issues',
                'response_time_hours': 4,
                'resolution_time_hours': 24,
                'priority': 'p3'
            },
            {
                'name': 'Low Priority SLA',
                'description': 'For P4 low priority issues',
                'response_time_hours': 8,
                'resolution_time_hours': 72,
                'priority': 'p4'
            }
        ]
        
        for sla_data in slas_data:
            sla, created = SLA.objects.get_or_create(
                name=sla_data['name'],
                defaults=sla_data
            )
            if created:
                self.stdout.write(f'Created SLA: {sla.name}')

    def create_assets(self):
        assets_data = [
            {
                'name': 'AHU-01',
                'asset_type': 'ahu',
                'location': 'Data Hall 1',
                'serial_number': 'AHU001-2023'
            },
            {
                'name': 'AHU-02',
                'asset_type': 'ahu',
                'location': 'Data Hall 2',
                'serial_number': 'AHU002-2023'
            },
            {
                'name': 'GEN-01',
                'asset_type': 'genset',
                'location': 'Generator Room',
                'serial_number': 'GEN001-2023'
            },
            {
                'name': 'GEN-02',
                'asset_type': 'genset',
                'location': 'Generator Room',
                'serial_number': 'GEN002-2023'
            },
            {
                'name': 'IAC-01',
                'asset_type': 'iac',
                'location': 'Data Hall 1 - Row A',
                'serial_number': 'IAC001-2023'
            },
            {
                'name': 'IAC-02',
                'asset_type': 'iac',
                'location': 'Data Hall 1 - Row B',
                'serial_number': 'IAC002-2023'
            },
            {
                'name': 'PUMP-01',
                'asset_type': 'pump',
                'location': 'Pump Room',
                'serial_number': 'PUMP001-2023'
            },
            {
                'name': 'RO-PLANT-01',
                'asset_type': 'ro_plant',
                'location': 'Water Treatment Room',
                'serial_number': 'RO001-2023'
            }
        ]
        
        for asset_data in assets_data:
            asset, created = Asset.objects.get_or_create(
                name=asset_data['name'],
                defaults=asset_data
            )
            if created:
                self.stdout.write(f'Created asset: {asset.name}')

    def create_tickets(self):
        users = list(User.objects.all())
        categories = list(TicketCategory.objects.all())
        assets = list(Asset.objects.all())
        slas = list(SLA.objects.all())
        
        tickets_data = [
            {
                'title': 'AHU-01 High Temperature Alert',
                'description': 'AHU-01 is showing high temperature readings. Supply air temperature is 18°C instead of normal 12°C. Need immediate investigation.',
                'priority': 'p1',
                'status': 'in_progress'
            },
            {
                'title': 'Generator Weekly Test Failed',
                'description': 'GEN-02 failed to start during weekly test. Engine cranks but does not fire. Fuel levels are normal.',
                'priority': 'p2',
                'status': 'open'
            },
            {
                'title': 'IAC Unit Alarm - Low Refrigerant',
                'description': 'IAC-01 showing low refrigerant alarm. Cooling capacity appears reduced.',
                'priority': 'p2',
                'status': 'pending'
            },
            {
                'title': 'Water Pump Vibration',
                'description': 'PUMP-01 showing excessive vibration during operation. May need bearing replacement.',
                'priority': 'p3',
                'status': 'resolved'
            },
            {
                'title': 'RO Plant Membrane Replacement',
                'description': 'Scheduled maintenance for RO plant membrane replacement. TDS levels increasing.',
                'priority': 'p3',
                'status': 'open'
            },
            {
                'title': 'Fire Suppression System Test',
                'description': 'Quarterly test of fire suppression system in Data Hall 1. Coordinate with operations.',
                'priority': 'p4',
                'status': 'closed'
            },
            {
                'title': 'HVAC Filter Replacement',
                'description': 'Monthly filter replacement for all AHU units. Filters showing high pressure drop.',
                'priority': 'p4',
                'status': 'in_progress'
            },
            {
                'title': 'UPS Battery Monitoring Alert',
                'description': 'UPS system showing battery monitoring alert. Need to check individual cell voltages.',
                'priority': 'p2',
                'status': 'open'
            }
        ]
        
        for i, ticket_data in enumerate(tickets_data):
            if not Ticket.objects.filter(title=ticket_data['title']).exists():
                # Assign random category and asset
                category = random.choice(categories) if categories else None
                asset = random.choice(assets) if assets else None
                created_by = random.choice(users)
                assigned_to = random.choice(users) if random.choice([True, False]) else None
                
                # Get appropriate SLA
                sla = None
                if slas:
                    priority_slas = [s for s in slas if s.priority == ticket_data['priority']]
                    sla = priority_slas[0] if priority_slas else None
                
                ticket = Ticket.objects.create(
                    title=ticket_data['title'],
                    description=ticket_data['description'],
                    priority=ticket_data['priority'],
                    status=ticket_data['status'],
                    category=category,
                    asset=asset,
                    created_by=created_by,
                    assigned_to=assigned_to,
                    sla=sla,
                    contact_name=f'Contact {i+1}',
                    contact_email=f'contact{i+1}@datacenter.com',
                    contact_phone=f'+1-555-{1000+i:04d}'
                )
                
                # Note: History entry will be created automatically by the model's save method
                
                self.stdout.write(f'Created ticket: {ticket.ticket_id}')

    def create_kb_articles(self):
        admin_user = User.objects.filter(is_superuser=True).first()
        categories = list(TicketCategory.objects.all())
        
        articles_data = [
            {
                'title': 'AHU Troubleshooting Guide',
                'content': '''# AHU Troubleshooting Guide

## Common Issues and Solutions

### High Temperature Alerts
1. Check air filters for blockage
2. Verify chilled water flow
3. Check damper positions
4. Inspect cooling coils

### Low Airflow
1. Check fan belt tension
2. Verify VFD settings
3. Inspect ductwork for obstructions
4. Check filter pressure drop

### Unusual Noises
1. Inspect fan bearings
2. Check for loose components
3. Verify belt alignment
4. Check motor mounts
''',
                'tags': 'hvac, ahu, troubleshooting, maintenance'
            },
            {
                'title': 'Generator Maintenance Checklist',
                'content': '''# Generator Maintenance Checklist

## Weekly Tests
- [ ] Start generator and run for 30 minutes
- [ ] Check oil level and condition
- [ ] Verify fuel level
- [ ] Test automatic transfer switch
- [ ] Check battery voltage

## Monthly Maintenance
- [ ] Change oil filter
- [ ] Check air filter
- [ ] Inspect belts and hoses
- [ ] Test emergency stop
- [ ] Load bank test

## Annual Service
- [ ] Replace spark plugs
- [ ] Service cooling system
- [ ] Replace fuel filters
- [ ] Comprehensive load test
''',
                'tags': 'generator, maintenance, checklist, power'
            },
            {
                'title': 'Fire Suppression System Procedures',
                'content': '''# Fire Suppression System Procedures

## Emergency Response
1. Evacuate all personnel immediately
2. Call emergency services (911)
3. Notify facility management
4. Do not re-enter until cleared

## System Testing
- Monthly: Visual inspection of components
- Quarterly: Functional test of detection system
- Annually: Full system discharge test

## Maintenance Requirements
- Check agent levels monthly
- Inspect nozzles and piping
- Test control panels
- Verify emergency procedures
''',
                'tags': 'fire, safety, suppression, emergency'
            }
        ]
        
        for article_data in articles_data:
            if not KnowledgeBaseArticle.objects.filter(title=article_data['title']).exists():
                article = KnowledgeBaseArticle.objects.create(
                    title=article_data['title'],
                    content=article_data['content'],
                    tags=article_data['tags'],
                    author=admin_user,
                    category=random.choice(categories) if categories else None,
                    is_published=True
                )
                self.stdout.write(f'Created KB article: {article.title}')