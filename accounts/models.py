from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, blank=True)
    company_size = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.user.email


class UserCredits(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credits')
    total_credits = models.IntegerField(default=10)
    used_credits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.available_credits()} credits"

    @property
    def available_credits(self):
        return self.total_credits - self.used_credits


class UserOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp')
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - OTP"