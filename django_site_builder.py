import os
import subprocess
import sys
import textwrap
import json
from datetime import datetime

def print_step(message):
    """Prints a formatted step message."""
    print(f"\n--- 🚀 {message} ---")

def get_user_input(prompt, default=None):
    """Gets user input with an optional default value."""
    response = input(f"{prompt} " + (f"[{default}]" if default else "") + ": ")
    return response or default

def update_settings_file(settings_path, app_name, db_choice, use_o365, project_name):
    """Intelligently updates the Django settings.py file."""
    with open(settings_path, 'r') as f:
        lines = f.readlines()

    # Add the new app to INSTALLED_APPS
    for i, line in enumerate(lines):
        if "'django.contrib.staticfiles'," in line:
            lines.insert(i + 1, f"    '{app_name}',\n")
            if use_o365 == 'yes':
                lines.insert(i + 2, "    'microsoft_auth',\n")
                lines.insert(i + 3, "    'django.contrib.sites',\n")
            break
    
    # Add context processor
    for i, line in enumerate(lines):
        if "'django.template.context_processors.request'," in line:
            lines.insert(i, f"                '{project_name}.context_processors.auth_enabled',\n")
            break

    # Add settings at the end of the file
    lines.append(f"\nAUTH_USER_MODEL = '{app_name}.User'\n")
    lines.append("LOGIN_REDIRECT_URL = '/'\nLOGOUT_REDIRECT_URL = '/'\n")

    if use_o365 == 'yes':
        lines.append("\nSITE_ID = 1\n")
        lines.append("\nAUTHENTICATION_BACKENDS = [\n")
        lines.append("    'microsoft_auth.backends.MicrosoftAuthenticationBackend',\n")
        lines.append("    'django.contrib.auth.backends.ModelBackend',\n")
        lines.append("]\n")
        lines.append("\nMICROSOFT_AUTH_CLIENT_ID = 'YOUR_CLIENT_ID'\n")
        lines.append("MICROSOFT_AUTH_CLIENT_SECRET = 'YOUR_CLIENT_SECRET'\n")
        lines.append("MICROSOFT_AUTH_TENANT_ID = 'YOUR_TENANT_ID'\n")
        lines.append("USER_O365_AUTH_ENABLED = True\n")
    else:
        lines.append("USER_O365_AUTH_ENABLED = False\n")

    if db_choice == 'postgres':
        db_settings_updated = False
        for i, line in enumerate(lines):
            if "'ENGINE': 'django.db.backends.sqlite3'," in line:
                lines[i] = "        'ENGINE': 'django.db.backends.postgresql',\n"
                lines[i+1] = textwrap.dedent("""
                    'NAME': 'your_db_name',
                    'USER': 'your_db_user',
                    'PASSWORD': 'your_db_password',
                    'HOST': 'localhost',
                    'PORT': '5432',
                """).replace("'", "        '")
                db_settings_updated = True
                break
    
    with open(settings_path, 'w') as f:
        f.writelines(lines)

def update_urls_file(urls_path, app_name, use_o365):
    """Intelligently updates the main urls.py file."""
    with open(urls_path, 'r') as f:
        lines = f.readlines()

    # Add include import
    for i, line in enumerate(lines):
        if "from django.urls import path" in line:
            lines[i] = "from django.urls import path, include\n"
            break

    # Add new URL patterns
    for i, line in enumerate(lines):
        if "path('admin/', admin.site.urls)," in line:
            lines.insert(i + 1, f"    path('', include('{app_name}.urls')),\n")
            lines.insert(i + 2, "    path('accounts/', include('django.contrib.auth.urls')),\n")
            if use_o365 == 'yes':
                lines.insert(i + 3, "    path('microsoft/', include('microsoft_auth.urls', namespace='microsoft_auth')),\n")
            break
            
    with open(urls_path, 'w') as f:
        f.writelines(lines)

def main():
    """Main function to run the Django project builder."""
    print("--- 🛠️ Interactive Django Ticketing System Builder ---")
    
    project_folder = get_user_input("Enter a name for the main project folder", "dc_ticketing_system")
    project_name = get_user_input("Enter a name for the Django configuration directory", "dc_config")
    app_name = get_user_input("Enter a name for your app", "tickets")
    db_choice = get_user_input("Use 'sqlite' or 'postgres' for the database?", "sqlite")
    use_o365 = get_user_input("Include Office 365 authentication? (yes/no)", "yes").lower()
    venv_name = "venv"

    # --- 1. Create Django Project in a new directory ---
    print_step(f"Creating Django project: {project_name}")
    parent_dir = os.getcwd()
    temp_venv_path = os.path.join(parent_dir, "temp_venv_for_django_admin")
    subprocess.run([sys.executable, '-m', 'venv', temp_venv_path], check=True, capture_output=True)
    if sys.platform == "win32":
        initial_django_admin_path = os.path.join(temp_venv_path, 'Scripts', 'django-admin.exe')
        initial_pip_path = os.path.join(temp_venv_path, 'Scripts', 'pip.exe')
    else:
        initial_django_admin_path = os.path.join(temp_venv_path, 'bin', 'django-admin')
        initial_pip_path = os.path.join(temp_venv_path, 'bin', 'pip')
    
    subprocess.run([initial_pip_path, 'install', 'django'], check=True, capture_output=True)
    subprocess.run([initial_django_admin_path, 'startproject', project_name, project_folder], check=True)
    
    if sys.platform == "win32":
        subprocess.run(['rmdir', '/S', '/Q', temp_venv_path], shell=True)
    else:
        subprocess.run(['rm', '-rf', temp_venv_path])
    
    # --- 2. Move into project and create final venv ---
    os.chdir(project_folder)
    print_step(f"Creating virtual environment: {venv_name}")
    subprocess.run([sys.executable, '-m', 'venv', venv_name], check=True)
    
    if sys.platform == "win32":
        pip_path = os.path.join(venv_name, 'Scripts', 'pip.exe')
        python_path = os.path.join(venv_name, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(venv_name, 'bin', 'pip')
        python_path = os.path.join(venv_name, 'bin', 'python')

    packages_to_install = ['django']
    if db_choice == 'postgres':
        packages_to_install.append('psycopg2-binary')
    if use_o365 == 'yes':
        packages_to_install.append('django-microsoft-auth')

    print_step(f"Installing {', '.join(packages_to_install)}")
    subprocess.run([pip_path, 'install'] + packages_to_install, check=True, capture_output=True)
    print("✅ Packages installed.")

    # --- 3. Create Django App ---
    print_step(f"Creating Django app: {app_name}")
    subprocess.run([python_path, 'manage.py', 'startapp', app_name], check=True)

    # --- 4. Generate requirements.txt ---
    print_step("Generating requirements.txt file")
    with open('requirements.txt', 'w') as f:
        subprocess.run([pip_path, 'freeze'], stdout=f, check=True)
    print("✅ requirements.txt created.")

    # --- 5. Generate Models ---
    print_step(f"Generating models in {app_name}/models.py")
    models_py_content = textwrap.dedent("""
        from django.db import models, OperationalError
        from django.contrib.auth.models import AbstractUser
        from django.conf import settings

        def get_next_ticket_id():
            try:
                last_ticket = Ticket.objects.all().order_by('id').last()
                if not last_ticket:
                    return 'RX-UG-INC-000001'
                last_id = int(last_ticket.ticket_id.split('-')[-1])
                new_id = last_id + 1
                return f'RX-UG-INC-{{new_id:06d}}'
            except (OperationalError, NameError):
                # This can happen on the very first migration when the Ticket table doesn't exist yet.
                return 'RX-UG-INC-000001'

        class User(AbstractUser):
            ROLE_CHOICES = (
                ('technician', 'Facilities Technician'),
                ('engineer', 'Facilities Engineer'),
                ('manager', 'Facilities Manager'),
                ('bms', 'BMS/Control Centre Staff'),
            )
            role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')

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

        class Ticket(models.Model):
            STATUS_CHOICES = [('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('closed', 'Closed')]
            PRIORITY_CHOICES = [('p1', 'P1 - Critical'), ('p2', 'P2 - High'), ('p3', 'P3 - Medium'), ('p4', 'P4 - Low')]
            
            ticket_id = models.CharField(max_length=20, unique=True, default=get_next_ticket_id)
            title = models.CharField(max_length=255)
            description = models.TextField()
            asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
            status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
            priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='p3')
            created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets')
            assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
            created_at = models.DateTimeField(auto_now_add=True)
            updated_at = models.DateTimeField(auto_now=True)
            resolution_notes = models.TextField(blank=True)

            def __str__(self):
                return f"{{self.ticket_id}}: {{self.title}}"
    """)
    with open(os.path.join(app_name, 'models.py'), 'w') as f: f.write(models_py_content)
    print("✅ models.py created.")

    # --- 6. Configure Admin ---
    print_step(f"Configuring admin in {app_name}/admin.py")
    admin_py_content = textwrap.dedent(f"""
        from django.contrib import admin
        from django.contrib.auth.admin import UserAdmin
        from .models import User, Asset, Ticket

        class CustomUserAdmin(UserAdmin):
            model = User
            fieldsets = UserAdmin.fieldsets + ((None, {{'fields': ('role',)}}),)
            add_fieldsets = UserAdmin.add_fieldsets + ((None, {{'fields': ('role',)}}),)

        @admin.register(Asset)
        class AssetAdmin(admin.ModelAdmin):
            list_display = ('name', 'asset_type', 'location', 'last_maintenance_date')
            list_filter = ('asset_type', 'location')
            search_fields = ('name', 'serial_number')

        @admin.register(Ticket)
        class TicketAdmin(admin.ModelAdmin):
            list_display = ('ticket_id', 'title', 'asset', 'status', 'priority', 'created_by', 'assigned_to', 'created_at')
            list_filter = ('status', 'priority', 'created_at')
            search_fields = ('title', 'description', 'ticket_id')
            raw_id_fields = ('asset', 'created_by', 'assigned_to')

        admin.site.register(User, CustomUserAdmin)
    """)
    with open(os.path.join(app_name, 'admin.py'), 'w') as f: f.write(admin_py_content)
    print("✅ admin.py configured.")

    # --- 7. Create Views and URLs ---
    print_step(f"Creating views and URLs for {app_name}")
    views_py_content = textwrap.dedent(f"""
        from django.shortcuts import render
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views.generic import ListView, DetailView
        from .models import Ticket

        class HomeView(LoginRequiredMixin, ListView):
            model = Ticket
            template_name = '{app_name}/home.html'
            context_object_name = 'tickets'
    """)
    with open(os.path.join(app_name, 'views.py'), 'w') as f: f.write(views_py_content)

    app_urls_py_content = textwrap.dedent(f"""
        from django.urls import path
        from .views import HomeView

        app_name = '{app_name}'
        urlpatterns = [
            path('', HomeView.as_view(), name='home'),
        ]
    """)
    with open(os.path.join(app_name, 'urls.py'), 'w') as f: f.write(app_urls_py_content)

    # --- 8. Create Templates ---
    print_step("Creating HTML templates")
    templates_dir = os.path.join(app_name, 'templates', app_name)
    os.makedirs(templates_dir, exist_ok=True)
    
    base_html_content = textwrap.dedent(f"""
        <!DOCTYPE html>
        <html lang="en" class="scroll-smooth">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{% block title %}}Data Centre Ticketing{{% endblock %}}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;700&family=Lato:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Lato', sans-serif; background-color: #FDFBF7; color: #3A3A5A; }}
                h1, h2, h3, h4, h5, h6 {{ font-family: 'Lora', serif; }}
            </style>
        </head>
        <body class="antialiased">
            <header class="bg-[#FDFBF7]/80 backdrop-blur-lg shadow-sm sticky top-0 z-50 border-b border-[#F5F0E8]">
                <nav class="container mx-auto px-6 lg:px-8">
                    <div class="flex items-center justify-between h-20">
                        <div class="flex items-center space-x-3">
                            <div class="w-9 h-9 bg-[#3A3A5A] rounded-lg flex items-center justify-center text-white font-bold text-xl font-serif">T</div>
                            <h1 class="text-xl font-bold text-[#3A3A5A]">DC Ticketing System</h1>
                        </div>
                        <div class="flex items-center space-x-4">
                            {{% if user.is_authenticated %}}
                                <span class="text-sm">Welcome, {{{{ user.first_name|default:user.username }}}}</span>
                                <a href="{{% url 'logout' %}}" class="text-sm font-medium text-red-600 hover:underline">Logout</a>
                            {{% else %}}
                                <a href="{{% url 'login' %}}" class="text-sm font-medium hover:underline">Login</a>
                            {{% endif %}}
                        </div>
                    </div>
                </nav>
            </header>
            <main class="container mx-auto px-6 lg:px-8 py-12">
                {{% block content %}}{{% endblock %}}
            </main>
        </body>
        </html>
    """)
    with open(os.path.join(templates_dir, 'base.html'), 'w') as f: f.write(base_html_content)

    home_html_content = textwrap.dedent(f"""
        {{% extends '{app_name}/base.html' %}}
        {{% block title %}}Dashboard{{% endblock %}}
        {{% block content %}}
        <h1 class="text-3xl font-bold text-[#3A3A5A] mb-8">Ticket Dashboard</h1>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {{% for ticket in tickets %}}
            <div class="bg-white p-6 rounded-lg shadow-md border border-slate-200">
                <div class="flex justify-between items-start">
                    <h2 class="text-xl font-bold text-[#3A3A5A]">{{{{ ticket.title }}}}</h2>
                    <span class="text-sm font-bold text-white px-2 py-1 rounded-full 
                        {{% if ticket.priority == 'p1' %}}bg-red-500
                        {{% elif ticket.priority == 'p2' %}}bg-orange-500
                        {{% else %}}bg-yellow-500{{% endif %}}">
                        {{{{ ticket.get_priority_display }}}}
                    </span>
                </div>
                <p class="text-sm text-slate-500 mt-1">{{{{ ticket.ticket_id }}}}</p>
                <p class="text-slate-600 my-4">{{{{ ticket.description|truncatewords:20 }}}}</p>
                <div class="border-t border-slate-200 pt-4 text-sm text-slate-500">
                    <p><strong>Asset:</strong> {{{{ ticket.asset|default:'N/A' }}}}</p>
                    <p><strong>Status:</strong> {{{{ ticket.get_status_display }}}}</p>
                    <p><strong>Assigned To:</strong> {{{{ ticket.assigned_to|default:'Unassigned' }}}}</p>
                </div>
            </div>
            {{% endfor %}}
        </div>
        {{% endblock %}}
    """)
    with open(os.path.join(templates_dir, 'home.html'), 'w') as f: f.write(home_html_content)
    
    # Auth templates
    os.makedirs(os.path.join(app_name, 'templates', 'registration'), exist_ok=True)
    login_html_content = textwrap.dedent(f"""
        {{% extends '{app_name}/base.html' %}}
        {{% block title %}}Login{{% endblock %}}
        {{% block content %}}
        <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-md">
            <h1 class="text-2xl font-bold text-center mb-6">Login</h1>
            {{% if user_o365_auth_enabled %}}
            <a href="{{% url 'microsoft_auth:auth' %}}" class="block w-full text-center bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 mb-4">
                Login with Office 365
            </a>
            <p class="text-center text-slate-500 my-4">OR</p>
            {{% endif %}}
            <form method="post">
                {{% csrf_token %}}
                {{{{ form.as_p }}}}
                <button type="submit" class="w-full bg-[#3A3A5A] text-white font-bold py-3 px-4 rounded-lg hover:bg-[#2c2c46]">Login</button>
            </form>
        </div>
        {{% endblock %}}
    """)
    with open(os.path.join(app_name, 'templates', 'registration', 'login.html'), 'w') as f: f.write(login_html_content)
    
    logged_out_html_content = textwrap.dedent(f"""
        {{% extends '{app_name}/base.html' %}}
        {{% block title %}}Logged Out{{% endblock %}}
        {{% block content %}}
        <div class="max-w-md mx-auto text-center">
            <h1 class="text-2xl font-bold mb-4">Logged Out</h1>
            <p>You have been successfully logged out.</p>
            <a href="{{% url 'login' %}}" class="mt-6 inline-block bg-[#3A3A5A] text-white font-bold py-3 px-8 rounded-lg">Login Again</a>
        </div>
        {{% endblock %}}
    """)
    with open(os.path.join(app_name, 'templates', 'registration', 'logged_out.html'), 'w') as f: f.write(logged_out_html_content)

    # --- 9. Update Settings and URLs ---
    print_step(f"Updating {project_name}/settings.py and {project_name}/urls.py")
    settings_path = os.path.join(project_name, 'settings.py')
    update_settings_file(settings_path, app_name, db_choice, use_o365, project_name)
    
    # Create context processor
    context_processor_content = textwrap.dedent(f"""
        from django.conf import settings

        def auth_enabled(request):
            return {{'user_o365_auth_enabled': getattr(settings, 'USER_O365_AUTH_ENABLED', False)}}
    """)
    with open(os.path.join(project_name, 'context_processors.py'), 'w') as f: f.write(context_processor_content)

    urls_path = os.path.join(project_name, 'urls.py')
    update_urls_file(urls_path, app_name, use_o365)
    
    # --- 10. Create Data Migration for Site model ---
    if use_o365 == 'yes':
        print_step("Creating data migration for default site")
        migrations_dir = os.path.join(app_name, 'migrations')
        migration_file_path = os.path.join(migrations_dir, '0002_create_default_site.py')
        
        data_migration_content = textwrap.dedent("""
            from django.db import migrations

            def create_default_site(apps, schema_editor):
                Site = apps.get_model('sites', 'Site')
                if not Site.objects.filter(pk=1).exists():
                    Site.objects.create(pk=1, domain='example.com', name='example.com')

            class Migration(migrations.Migration):

                dependencies = [
                    ('sites', '0002_alter_domain_unique'), # Dependency on the sites app's migration
                    ('tickets', '0001_initial'),
                ]

                operations = [
                    migrations.RunPython(create_default_site),
                ]
        """)
        with open(migration_file_path, 'w') as f: f.write(data_migration_content)
        print(f"✅ Created {migration_file_path}")


    # --- 11. Create Sample Data ---
    print_step("Creating sample data fixture")
    fixtures_dir = os.path.join(app_name, 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)
    now_iso = datetime.utcnow().isoformat() + "Z"
    sample_data = [
      { "model": f"{app_name}.asset", "pk": 1, "fields": { "name": "Generator Set 1", "asset_type": "genset", "location": "Basement Level" } },
      { "model": f"{app_name}.asset", "pk": 2, "fields": { "name": "AHU-03", "asset_type": "ahu", "location": "Roof Level" } },
      { "model": f"{app_name}.ticket", "pk": 1, "fields": { "ticket_id": "RX-UG-INC-000001", "title": "Generator failed to start during weekly test", "description": "During the weekly automated test, Generator 1 failed to kick in. Manual start was also unsuccessful. Requires immediate investigation.", "asset": 1, "status": "open", "priority": "p1", "created_by": 1, "assigned_to": None, "created_at": now_iso, "updated_at": now_iso } },
      { "model": f"{app_name}.ticket", "pk": 2, "fields": { "ticket_id": "RX-UG-INC-000002", "title": "AHU-03 making unusual noise", "description": "A high-pitched whining sound is coming from AHU-03. The unit is still operational but the noise is abnormal.", "asset": 2, "status": "open", "priority": "p3", "created_by": 1, "assigned_to": None, "created_at": now_iso, "updated_at": now_iso } }
    ]
    with open(os.path.join(fixtures_dir, 'sample_data.json'), 'w') as f:
        json.dump(sample_data, f, indent=2)
    print("✅ sample_data.json created.")

    # --- 12. Create README.md ---
    print_step("Generating README.md file")
    readme_content = textwrap.dedent(f"""
        # {project_folder.replace('_', ' ').title()}

        This is a Django-based ticketing system for data centre grey space management, built according to the ITIL model.

        ---

        ## Setup and Installation

        1.  **Activate the virtual environment:**
            ```bash
            # For macOS/Linux
            source {venv_name}/bin/activate

            # For Windows
            .\\{venv_name}\\Scripts\\activate
            ```

        2.  **Install dependencies (if needed):**
            ```bash
            pip install -r requirements.txt
            ```

        3.  **Configure your settings:**
            Open `{project_name}/settings.py` and update your database credentials (if using PostgreSQL) and/or your Office 365 credentials.

        4.  **Run database migrations:**
            ```bash
            python manage.py makemigrations
            python manage.py migrate
            ```

        5.  **Create a superuser:**
            ```bash
            python manage.py createsuperuser
            ```

        6.  **Load sample data (optional):**
            ```bash
            python manage.py loaddata sample_data.json
            ```

        7.  **Run the development server:**
            ```bash
            python manage.py runserver
            ```

        The application will be available at `http://127.0.0.1:8000`.
    """)
    with open('README.md', 'w') as f:
        f.write(readme_content)
    print("✅ README.md created.")


    # --- Final Instructions ---
    print("\n--- ✅ Project Setup Complete! ---")
    print("\nTo launch your new ticketing system, follow these steps:")
    if sys.platform == "win32":
        print(f"1. Activate the virtual environment: .\\{project_folder}\\{venv_name}\\Scripts\\activate")
    else:
        print(f"1. Navigate into your project directory: cd {project_folder}")
        print(f"2. Activate the virtual environment: source {venv_name}/bin/activate")
    if db_choice == 'postgres' or use_o365 == 'yes':
        print(f"3. IMPORTANT: Edit '{project_name}/settings.py' and fill in your database and/or Office 365 credentials.")
    print("4. Create the database migrations: python manage.py makemigrations")
    print("5. Apply the migrations: python manage.py migrate")
    print("6. Create an admin user: python manage.py createsuperuser")
    print("7. Load sample data: python manage.py loaddata sample_data.json")
    print("8. Run the development server: python manage.py runserver")
    print("\nThen, open your web browser and go to: http://127.0.0.1:8000")

if __name__ == "__main__":
    main()
