from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form. Sets user as inactive pending approval.
        """
        from allauth.account.utils import user_email, user_field, user_username
        
        data = form.cleaned_data
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        username = data.get('username')
        
        user_email(user, email)
        user_username(user, username)
        if first_name:
            user_field(user, 'first_name', first_name)
        if last_name:
            user_field(user, 'last_name', last_name)
        if 'password1' in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()
        
        # Set user as inactive pending approval
        user.is_active = False
        user.role = 'technician'  # Default role
        
        self.populate_username(request, user)
        if commit:
            user.save()
            # Notify admins of new signup request
            self.notify_admins_of_signup(user, data)
        return user
    
    def notify_admins_of_signup(self, user, form_data):
        """Notify superusers of new signup request"""
        try:
            admins = User.objects.filter(is_superuser=True, is_active=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = f'New Account Request - {user.get_full_name()}'
                message = f"""
                A new user has requested access to the Knowledge Engine system:
                
                Name: {user.get_full_name()}
                Email: {user.email}
                Department: {form_data.get('department', 'Not specified')}
                Reason: {form_data.get('reason', 'Not specified')}
                Manager Email: {form_data.get('manager_email', 'Not specified')}
                
                Please review and approve/deny this request in the Django admin panel.
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=True,
                )
        except Exception:
            pass  # Don't fail signup if email fails
    
    def respond_user_inactive(self, request, user):
        """Custom response for inactive users"""
        messages.info(
            request,
            'Your account request has been submitted and is pending approval. '
            'You will receive an email notification once your account is activated.'
        )
        return redirect('account_login')
    
    def login(self, request, user):
        """Override login to check if user is approved"""
        if not user.is_active:
            messages.error(
                request,
                'Your account is pending approval. Please contact an administrator.'
            )
            return redirect('account_login')
        return super().login(request, user)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login. Social logins also require approval.
        """
        user = sociallogin.user
        user.set_unusable_password()
        
        # Extract user info from social account
        if sociallogin.account.provider == 'google':
            extra_data = sociallogin.account.extra_data
            user.first_name = extra_data.get('given_name', '')
            user.last_name = extra_data.get('family_name', '')
            user.email = extra_data.get('email', '')
            
        elif sociallogin.account.provider == 'microsoft':
            extra_data = sociallogin.account.extra_data
            user.first_name = extra_data.get('givenName', '')
            user.last_name = extra_data.get('surname', '')
            user.email = extra_data.get('mail', '') or extra_data.get('userPrincipalName', '')
        
        # Set default role and require approval for social login users
        user.role = 'technician'  # Default role
        user.is_active = False  # Require approval
            
        user.save()
        
        # Notify admins of social signup
        self.notify_admins_of_social_signup(user, sociallogin)
        
        return user
    
    def notify_admins_of_social_signup(self, user, sociallogin):
        """Notify superusers of new social signup request"""
        try:
            admins = User.objects.filter(is_superuser=True, is_active=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                provider_name = sociallogin.account.provider.title()
                subject = f'New {provider_name} Account Request - {user.get_full_name()}'
                message = f"""
                A new user has requested access to the Knowledge Engine system via {provider_name}:
                
                Name: {user.get_full_name()}
                Email: {user.email}
                Provider: {provider_name}
                
                Please review and approve/deny this request in the Django admin panel.
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=True,
                )
        except Exception:
            pass  # Don't fail signup if email fails
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).
        """
        # If user exists with this email, connect the account
        if sociallogin.is_existing:
            return
        
        if sociallogin.user.email:
            try:
                user = User.objects.get(email=sociallogin.user.email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass