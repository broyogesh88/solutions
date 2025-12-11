from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from .forms import SignupForm, LoginForm, OTPVerificationForm, generate_otp
from .models import UserProfile, UserCredits, UserOTP
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse



BLOCKED_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']


def is_workspace_email(email):
    """Check if email is a workspace email (not personal)"""
    domain = email.lower().split('@')[-1]
    return domain not in BLOCKED_DOMAINS


def send_otp_email(user, otp_code):
    """Send OTP email to user"""
    subject = "Email Verification - Your OTP"
    message = f"""
    Hello {user.email},
    
    Your OTP for email verification is: {otp_code}
    
    Please enter this OTP to verify your email and complete signup.
    
    Best regards,
    Dashboard Team
    """
    try:
        send_mail(
            subject,
            message,
            'noreply@dashboard.com',
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def login_page(request):
    """Handle both login and signup on the same page"""
    
    # If user is already logged in, redirect to profile
    if request.user.is_authenticated:
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile and profile.company_name and profile.company_size:
            return redirect("profile")
        else:
            return redirect("complete_profile")
    
    mode = request.GET.get('mode', 'login')  # 'login' or 'signup'
    login_form = LoginForm()
    signup_form = SignupForm()
    error = None
    
    if request.method == "POST":
        if 'login_submit' in request.POST:
            # Handle login
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                email = login_form.cleaned_data['email']
                password = login_form.cleaned_data['password']
                
                # Check if email exists
                try:
                    user_obj = User.objects.get(email=email)
                    
                    # Check if email is verified
                    try:
                        otp_obj = UserOTP.objects.get(user=user_obj)
                        if not otp_obj.is_verified:
                            messages.error(request, "Please verify your email first.")
                            error = "Please verify your email first."
                            return redirect(reverse('verify_otp') + f'?email={email}')
                    except UserOTP.DoesNotExist:
                        # No OTP record means email is verified (old users)
                        pass
                    
                    user = authenticate(request, username=user_obj.username, password=password)
                    
                    if user is not None:
                        # Verify workspace email
                        if not is_workspace_email(email):
                            messages.error(request, "Only workspace emails are allowed.")
                            error = "Only workspace emails are allowed."
                        else:
                            login(request, user)
                            # Check if profile is complete
                            profile = UserProfile.objects.filter(user=user).first()
                            if not profile or not profile.company_name or not profile.company_size:
                                return redirect("complete_profile")
                            return redirect("profile")
                    else:
                        error = "Invalid email or password."
                except User.DoesNotExist:
                    error = "Invalid email or password."
            else:
                error = "Please enter valid credentials."
                
        elif 'signup_submit' in request.POST:
            # Handle signup
            signup_form = SignupForm(request.POST)
            if signup_form.is_valid():
                email = signup_form.cleaned_data['email']
                
                # Validate workspace email
                if not is_workspace_email(email):
                    error = "Only workspace emails are allowed. Personal Gmail accounts are not permitted."
                    mode = 'signup'
                elif User.objects.filter(email=email).exists():
                    error = "This email is already registered."
                    mode = 'signup'
                else:
                    # Create user
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=signup_form.cleaned_data['password']
                    )

                    # Create profile
                    UserProfile.objects.create(
                        user=user,
                        company_name=signup_form.cleaned_data['company_name'],
                        company_size=signup_form.cleaned_data['company_size'],
                    )
                    
                    # Create credits
                    UserCredits.objects.create(user=user, total_credits=10)
                    
                    # Generate and send OTP
                    otp_code = generate_otp()
                    UserOTP.objects.create(user=user, otp_code=otp_code, is_verified=False)
                    
                    if send_otp_email(user, otp_code):
                        messages.success(request, "OTP sent to your email. Please verify to continue.")
                        return redirect(f"/verify-otp/?email={email}")
                    else:
                        messages.error(request, "Error sending OTP. Please try again.")
                        user.delete()
                        error = "Error sending OTP. Please try again."
            else:
                error = "Please fix the errors below."
                mode = 'signup'

    return render(request, "login.html", {
        'mode': mode,
        'login_form': login_form,
        'signup_form': signup_form,
        'error': error
    })


def verify_otp(request):
    """Verify OTP and activate account"""
    email = request.GET.get('email')
    
    if not email:
        return redirect("login")
    
    try:
        user = User.objects.get(email=email)
        otp_obj = UserOTP.objects.get(user=user)
    except (User.DoesNotExist, UserOTP.DoesNotExist):
        messages.error(request, "Invalid verification link.")
        return redirect("login")
    
    # If already verified, redirect to login
    if otp_obj.is_verified:
        messages.info(request, "Email already verified. Please login.")
        return redirect("login")
    
    error = None
    
    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            
            if entered_otp == otp_obj.otp_code:
                # OTP is correct, mark as verified
                otp_obj.is_verified = True
                otp_obj.save()
                
                messages.success(request, "Email verified successfully! You can now login.")
                return redirect("login")
            else:
                error = "Invalid OTP. Please try again."
        else:
            error = "Please enter a valid OTP."
    else:
        form = OTPVerificationForm()
    
    return render(request, "verify_otp.html", {
        'email': email,
        'form': form,
        'error': error
    })


def resend_otp(request):
    """Resend OTP to user email"""
    email = request.GET.get('email')
    
    if not email:
        return redirect("login")
    
    try:
        user = User.objects.get(email=email)
        otp_obj = UserOTP.objects.get(user=user)
    except (User.DoesNotExist, UserOTP.DoesNotExist):
        messages.error(request, "Invalid email.")
        return redirect("login")
    
    # Generate new OTP
    otp_code = generate_otp()
    otp_obj.otp_code = otp_code
    otp_obj.save()
    
    if send_otp_email(user, otp_code):
        messages.success(request, "OTP resent to your email.")
        return redirect(f"/verify-otp/?email={email}")
    else:
        messages.error(request, "Error resending OTP. Please try again.")
        return redirect(f"/verify-otp/?email={email}")


@login_required(login_url="login")
def complete_profile(request):
    """Complete user profile - used for both regular and OAuth users"""
    user = request.user
    
    # Verify user has workspace email
    if not is_workspace_email(user.email):
        logout(request)
        messages.error(request, "Only workspace emails are allowed.")
        return redirect("login")
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Create credits if doesn't exist
    UserCredits.objects.get_or_create(user=user, defaults={'total_credits': 10})

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        company_size = request.POST.get("company_size", "").strip()

        if not company_name or not company_size:
            error = "All fields are required."
            return render(request, "complete_profile.html", {
                "error": error,
                "user": user
            })

        # Update profile with company details
        profile.company_name = company_name
        profile.company_size = company_size
        profile.save()

        messages.success(request, "Profile completed successfully!")
        return redirect("profile")

    return render(request, "complete_profile.html", {"user": user})


@login_required(login_url="login")
def profile(request):
    """Display user profile with available apps and credits"""
    # Verify user has workspace email
    if not is_workspace_email(request.user.email):
        logout(request)
        messages.error(request, "Only workspace emails are allowed.")
        return redirect("login")
    
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # If profile doesn't exist, redirect to complete it
        return redirect("complete_profile")
    
    # Get or create credits
    credits, created = UserCredits.objects.get_or_create(user=request.user, defaults={'total_credits': 10})
    
    # Define available apps/solutions
    apps = [
        {
            'name': 'Qlx',
            'description': 'Quick learning experience platform for seamless knowledge acquisition',
            'icon': '⚡',
            'url': '/qlx/',
            'color': '#FF6B6B'
        },
        {
            'name': 'Vta',
            'description': 'Virtual teaching assistant to help with learning and training',
            'icon': '🎓',
            'url': '/vta/',
            'color': '#4ECDC4'
        },
        {
            'name': 'Pulseiq',
            'description': 'Real-time intelligence and analytics for data-driven decisions',
            'icon': '📊',
            'url': '/pulseiq/',
            'color': '#45B7D1'
        },
        {
            'name': 'Docmind',
            'description': 'Intelligent document analysis and processing tool',
            'icon': '📄',
            'url': '/docmind/',
            'color': '#96CEB4'
        },
        {
            'name': 'Askx',
            'description': 'Advanced AI-powered question answering system',
            'icon': '💡',
            'url': '/askx/',
            'color': '#FFEAA7'
        },
        {
            'name': 'ARL',
            'description': 'Adaptive Resource Learning system for personalized education',
            'icon': '🎯',
            'url': '/arl/',
            'color': '#DDA15E'
        },
    ]
    
    return render(request, "profile.html", {
        "user": request.user,
        "profile": profile,
        "credits": credits,
        "apps": apps
    })


def signup(request):
    """Redirect to login page with signup mode"""
    return redirect("login?mode=signup")


def logout_user(request):
    """Logout user and redirect to login"""
    logout(request)
    return redirect("login")