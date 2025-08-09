# Production-grade Testing Guide for DjangoSiteBuilder

This document outlines a robust, production-grade testing strategy for the DjangoSiteBuilder project. It covers test types, tools, patterns, coverage, performance/security checks, and CI recommendations tailored to this codebase (Django 5.2.5, django-allauth).

## Goals
- Correctness: Features do what they claim for all supported inputs.
- Security: Authentication, authorization, CSRF, and sensitive flows are correct.
- Reliability: Flows work across refactors; regressions are caught early.
- Performance: Avoid N+1 queries and slow endpoints; keep page loads efficient.

## Test Pyramid and Scope
1. Unit tests (largest): models, forms, utilities, adapters
2. Integration tests: views, URLs, middleware, template logic
3. Functional/E2E (smallest): full flows like login → dashboard → logout

## Tools and Conventions
- Built-in Django test runner (unittest) via `python manage.py test`
- Optional (future): pytest + pytest-django + factory_boy for improved DX
- Coverage with coverage.py (optional but recommended)

## Project-specific Areas to Test

### 1) Authentication and Account Flows (Allauth)
- Local login form posts to `account_login` and redirects to `/dashboard/` on success
- Inactive users cannot log in (CustomAccountAdapter/CustomSocialAccountAdapter)
- Logout via `users/logout/` shows success message and redirects to login
- Password reset flow renders all steps and updates password
- Social login initiation links exist for Google/Microsoft (no provider round-trip in unit tests)

Sample assertions:
- 302 → `/dashboard/` for active users; 200 with errors for bad credentials
- Message framework shows pending-approval notice if `is_active=False`
- Password reset emails captured in `django.core.mail.outbox`

### 2) Authorization and Permissions
- Staff-only views (e.g., user list, admin create user) return 302 to login for anonymous, 403/redirect for non-staff, 200 for staff
- Users can access only their own profile unless staff
- `change_password` requires login and updates session auth hash

### 3) Domain Models and Business Logic
- Ticket ID generation format `RX-UG-INC-000001` increments correctly
- SLA-driven properties (is_overdue, time_to_first_response/resolution)
- Comment save sets `first_response_at` for first staff comment
- History entries ordering and display

### 4) Forms
- User creation forms validate password match, required fields
- Ticket forms optional fields behavior; queryset restrictions (assigned_to roles)

### 5) Views and Templates
- Pages render with required context keys
- Templates include expected elements/links (e.g., login fields, forgot password link)
- Pagination behavior on list views

### 6) Emails
- Using console backend in dev; in tests verify `len(mail.outbox)` and content

### 7) Performance
- Use `assertNumQueries` to catch N+1 on list/detail pages
- Ensure queryset optimizations with `select_related/prefetch_related` where applicable

## Example Test Skeletons

```python
# tests/test_auth.py
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="secret", is_active=True
        )

    def test_login_success_redirects_to_dashboard(self):
        resp = self.client.post(reverse("account_login"), {
            "login": "alice",
            "password": "secret",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/dashboard/")

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(reverse("account_login"), {
            "login": "alice",
            "password": "secret",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "pending approval")

class PasswordResetTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_sends_email(self):
        User.objects.create_user("bob", email="bob@example.com", password="x")
        resp = self.client.post(reverse("account_reset_password"), {"email": "bob@example.com"})
        self.assertEqual(resp.status_code, 302)
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].body.lower())
```

```python
# tests/test_permissions.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class StaffOnlyViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tech", password="x", is_active=True)
        self.staff = User.objects.create_user("admin", password="x", is_active=True, is_staff=True)

    def test_user_list_requires_staff(self):
        url = reverse("users:list")
        # anonymous
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        # regular user
        self.client.login(username="tech", password="x")
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)
        # staff
        self.client.login(username="admin", password="x")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
```

```python
# tests/test_models.py
from django.test import TestCase
from tickets.models import Ticket, TicketCategory
from django.contrib.auth import get_user_model

User = get_user_model()

class TicketModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="x")
        self.cat = TicketCategory.objects.create(name="Power")

    def test_ticket_id_sequence(self):
        t1 = Ticket.objects.create(title="A", description="d", created_by=self.user)
        self.assertTrue(t1.ticket_id.endswith("000001"))
        t2 = Ticket.objects.create(title="B", description="d", created_by=self.user)
        self.assertTrue(t2.ticket_id.endswith("000002"))
```

## Running Tests
- Run all tests: `python manage.py test --parallel` (uses available CPU cores)
- Specific app: `python manage.py test tickets`
- With verbosity: `python manage.py test -v 2`

## Coverage (recommended)
1. Install: `pip install coverage`
2. Run: `coverage run manage.py test --parallel`  
3. Report: `coverage report -m` or `coverage html`

Target: ≥90% for critical modules (auth, adapters, models, permissions).

## Performance Checks
- Use `self.assertNumQueries(N)` around hot views
- Add select_related/prefetch_related where needed
- Consider `django-silk` or `django-debug-toolbar` locally (do not enable in prod)

## Security Testing
- Enforce CSRF checks in tests where needed: `Client(enforce_csrf_checks=True)`
- Ensure inactive users cannot log in
- Verify access control on every staff/admin-only endpoint
- Validate password reset tokens and flows fully complete

## Test Data and Fixtures
- Prefer factory-style creation in tests over large static fixtures
- Keep data minimal; avoid cross-test coupling

## Temporary Media for Upload Tests
```python
from django.test import override_settings
import tempfile

TEMP_MEDIA = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadTests(TestCase):
    ...
```

## Migrations and Schema Consistency
- Ensure migrations are current: `python manage.py makemigrations --check --dry-run`
- Run migrations in CI before tests: `python manage.py migrate --noinput`

## Continuous Integration (suggested)
- Use GitHub Actions to run: lint (optional), makemigrations check, migrate, tests, coverage
- Fail the build if tests or coverage threshold fail

## Future Enhancements
- Adopt pytest + pytest-django for richer assertions and fixtures
- Add Playwright-based smoke E2E for the critical auth flow
- Integrate pre-commit hooks (black, isort, flake8/ruff) to keep code quality high
