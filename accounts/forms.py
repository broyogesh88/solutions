from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, UserOTP
import random


class LoginForm(forms.Form):
    """Form for user login with email and password"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'required': True
        })
    )


class SignupForm(forms.ModelForm):
    """Form for user signup with company details"""
    
    class Meta:
        model = User
        fields = ['email', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your work email',
                'required': True
            }),
        }

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'required': True
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'required': True
        })
    )
    company_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Company name',
            'required': True
        })
    )
    company_size = forms.ChoiceField(
        choices=[
            ("", "Select company size"),
            ("<50", "< 50"),
            ("50-100", "50 - 100"),
            ("100-500", "100 - 500"),
            (">500", "> 500"),
        ],
        widget=forms.Select(attrs={
            'class': 'form-input',
            'required': True
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter 6-digit OTP',
            'required': True,
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data['otp']
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain only numbers.")
        return otp


def generate_otp():
    """Generate a random 6-digit OTP"""
    return str(random.randint(100000, 999999))