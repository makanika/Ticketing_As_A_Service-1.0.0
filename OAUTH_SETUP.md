# Google/Microsoft OAuth Setup for django-allauth

This guide explains how to set up Google and Microsoft OAuth for the project using django-allauth.

Prerequisites:
- The project is running locally at http://127.0.0.1:8000
- Allauth is installed and configured (already in this project)

## 1) Create Social Applications in Django Admin

Open Django admin:
- http://127.0.0.1:8000/admin

Steps:
1. Go to "Social applications" > "Add"
2. Create one application for Google
3. Create another application for Microsoft
4. For each application:
   - Provider: select Google or Microsoft
   - Name: any name (e.g., "Google OAuth Local", "Microsoft OAuth Local")
   - Client id and Secret: paste from the provider console
   - Sites: add your site (SITE_ID = 1)
     - If needed, edit the Sites entry to use domain: `127.0.0.1:8000` (Admin > Sites)

## 2) Configure Redirect URLs in Provider Consoles

Use these callback URLs exactly as shown:
- Google:     `http://127.0.0.1:8000/accounts/google/login/callback/`
- Microsoft:  `http://127.0.0.1:8000/accounts/microsoft/login/callback/`

Provider console locations (high-level):
- Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client IDs
- Microsoft Entra ID (Azure AD) > App registrations > Your App > Authentication

Ensure:
- The callback/redirect URLs match exactly
- For local dev, allow HTTP and localhost/127.0.0.1

## 3) Verification Checklist

- Normal login: Go to `/accounts/login/`, log in with an active user; you should land on `/dashboard/`.
- Social login: Click Microsoft/Google; you should be redirected to the provider auth (after adding SocialApp entries).
- Forgot password: Click "Forgot password?"; submit any email. You'll see a success page, and the email content appears in the console log.
- Signup: `/accounts/signup/` creates an inactive user; admin must activate them in Django admin before they can log in.

## Notes and Tips
- Local email is configured to console backend; reset and confirmation emails will print in the runserver console.
- In this project, new accounts (including social) are created inactive and require admin approval.
- For production, update Sites domain, add HTTPS, set real email backend, and create new SocialApp entries with production callback URLs.

## Optional Help
If you want, we can:
- Update the Sites framework domain to `127.0.0.1:8000` for consistency.
- Pre-create SocialApp objects if you provide the client IDs/secrets.
- Add an admin "Approve user" action to toggle active quickly.
