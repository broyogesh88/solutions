from allauth.account.signals import user_logged_in
from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from .models import UserProfile, UserCredits


BLOCKED_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']


def is_workspace_email(email):
    """Check if email is a workspace email (not personal)"""
    domain = email.lower().split('@')[-1]
    return domain not in BLOCKED_DOMAINS


@receiver(pre_social_login)
def handle_pre_social_login(sender, request, sociallogin, **kwargs):
    """Validate workspace email before social login"""
    email = sociallogin.account.extra_data.get('email', '').lower()
    
    if email and not is_workspace_email(email):
        messages.error(request, "Only workspace emails are allowed. Personal Gmail accounts are not permitted.")
        raise ValueError("Only workspace emails are allowed.")


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """Handle login for both regular and Google OAuth users"""
    email = user.email.lower()
    
    # Check if email is workspace email
    if not is_workspace_email(email):
        logout(request)
        messages.error(request, "Only workspace emails are allowed. Personal Gmail accounts are not permitted.")
        return
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Get or create credits (10 credits per user)
    credits, created = UserCredits.objects.get_or_create(user=user)
    
    # If profile is incomplete (new user from Gmail OAuth), redirect to complete it
    if not profile.company_name or not profile.company_size:
        # Store in session so we can check in middleware or view
        request.session["needs_profile_completion"] = True