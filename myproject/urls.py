from django.contrib import admin
from django.urls import path, include
from accounts import views

urlpatterns = [
    # Include allauth URLs for Google OAuth
    path("accounts/", include("allauth.urls")),
    
    path("login/", views.login_page, name="login"),
    path("signup/", views.signup, name="signup"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("profile/", views.profile, name="profile"),
    path("logout/", views.logout_user, name="logout"),

    path("admin/", admin.site.urls),
    path("", views.login_page, name="home"),
]