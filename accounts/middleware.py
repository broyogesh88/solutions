from django.shortcuts import redirect
from .models import UserProfile


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated and needs profile completion
        if request.user.is_authenticated:
            # Skip for certain URLs
            if request.path not in ['/complete-profile/', '/logout/', '/admin/', '/accounts/logout/']:
                try:
                    profile = UserProfile.objects.get(user=request.user)
                    # If profile is incomplete, redirect to complete profile
                    if not profile.company_name or not profile.company_size:
                        if request.path != '/complete-profile/':
                            return redirect('complete_profile')
                except UserProfile.DoesNotExist:
                    # Profile doesn't exist, redirect to create it
                    if request.path != '/complete-profile/':
                        return redirect('complete_profile')
        
        response = self.get_response(request)
        return response