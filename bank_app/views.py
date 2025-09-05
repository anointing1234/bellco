from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from email.mime.image import MIMEImage
from decimal import Decimal
from datetime import datetime
import threading
import random
import string
import os

from .models import (
    Account, AccountBalance, Card, Transaction, CurrencyBalance, Deposit,
    TransferCode, Transfer, Beneficiary, ExchangeRate, Exchange,
    LoanRequest, ResetPassword
)

# -------------------
# Async email helpers
# -------------------

def async_send_mail(*args, **kwargs):
    """Send email asynchronously in a thread."""
    threading.Thread(target=lambda: _send(*args, **kwargs), daemon=True).start()

def _send(*args, **kwargs):
    try:
        if 'instance' in kwargs:
            kwargs['instance'].send(fail_silently=kwargs.get('fail_silently', False))
        else:
            send_mail(*args, **kwargs)
    except Exception as e:
        print(f"⚠️ Async email failed: {e}")

# -------------------
# Home / Static Pages
# -------------------

def home_page(request):
    return render(request, 'home_page/index.html')

def contact_us(request):
    return render(request, 'home_page/Contact-Us.html')

def Branch_location(request):
    return render(request, 'home_page/Branch-Locations.html')

def Mortgage_Team(request):
    return render(request, 'home_page/Mortgage-Team.html')

def Our_Legacy(request):
    return render(request, 'home_page/Our-Legacy.html')

def Checking(request):
    return render(request, 'home_page/Checking.html')

def Savings(request):
    return render(request, 'home_page/Savings.html')

def Catastrophe_Savings(request):
    return render(request, 'home_page/Catastrophe-Savings.html')

def cd_ira(request):
    return render(request, 'home_page/CD-IRA.html')

def Business_Checking(request):
    return render(request, 'home_page/Business-Checking.html')

def Rates(request):
    return render(request, 'home_page/Rates.html')

def Construction(request):
    return render(request, 'home_page/Construction.html')

def Mortgage_Loans(request):
    return render(request, 'home_page/Mortgage-Loans.html')

def Calculators(request):
    return render(request, 'home_page/Calculators.html')

def Online_Services(request):
    return render(request, 'home_page/Online-Services.html')

def Card_Services(request):
    return render(request, 'home_page/Card-Services.html')

def Additional_Services(request):
    return render(request, 'home_page/Additional-Services.html')

def We_Care(request):
    return render(request, 'home_page/We-Care.html')

def Online_Education(request):
    return render(request, 'home_page/Online-Education.html')

def Security(request):
    return render(request, 'home_page/Security.html')

def Credit_Cards(request):
    return render(request, 'home_page/Credit-Cards.html')

def home_buying(request):
    return render(request, 'home_page/Home-Buying.html')

def Refinance_Equity(request):
    return render(request, 'home_page/Refinance-Equity copy.html')

# -------------------
# Authentication Views
# -------------------

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        remember = request.POST.get('remember') == 'on'

        if not identifier or not password:
            return JsonResponse({'success': False, 'message': 'Account ID and password are required.'}, status=400)

        user = None
        account = Account.objects.filter(account_id=identifier).first()
        if account:
            user = authenticate(request, email=account.email, password=password)
        else:
            user = authenticate(request, email=identifier, password=password)

        if user:
            login(request, user)
            request.session.set_expiry(1209600 if remember else 0)
            return JsonResponse({'success': True, 'message': 'Login successful!', 'redirect_url': '/dashboard/'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid account ID or password.'}, status=401)

    return render(request, 'forms/login.html')

def signup_view(request):
    return render(request, 'forms/signup.html')

def generate_unique_account_id():
    length = 5
    characters = string.ascii_uppercase + string.digits
    while True:
        account_id = ''.join(random.choices(characters, k=length))
        if not Account.objects.filter(account_id=account_id).exists():
            return account_id

def register_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    email = request.POST.get('email', '').strip()
    gender = request.POST.get('gender', '')
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')

    errors = []
    if not first_name: errors.append("First name is required.")
    if not last_name: errors.append("Last name is required.")
    if not phone_number or not (10 <= len(phone_number.replace('+', '')) <= 15 and phone_number.replace('+', '').isdigit()):
        errors.append("Enter a valid phone number (10-15 digits).")
    if not email or '@' not in email or '.' not in email: errors.append("Enter a valid email address.")
    if Account.objects.filter(email=email).exists(): errors.append("This email is already registered.")
    if Account.objects.filter(phone_number=phone_number).exists(): errors.append("This phone number is already in use.")
    if gender not in ['M', 'F', 'O']: errors.append("Please select a valid gender.")
    if not password or len(password) < 8: errors.append("Password must be at least 8 characters long.")
    if password != confirm_password: errors.append("Passwords do not match.")

    if errors:
        return JsonResponse({'success': False, 'message': "\n".join(errors)}, status=400)

    account_id = generate_unique_account_id()
    try:
        user = Account.objects.create_user(
            email=email, password=password, first_name=first_name,
            last_name=last_name, phone_number=phone_number, gender=gender,
            account_id=account_id
        )

        current_year = datetime.now().year
        email_subject = 'Welcome to Belco Community Credit Union'
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <img src="cid:Belco_logo.png" alt="Belco Logo" style="width: 150px; margin-bottom: 20px;">
                <h2>Welcome, {user.first_name} {user.last_name}!</h2>
                <p>Your account has been successfully created.</p>
                <p><strong>Account ID:</strong> {user.account_id}</p>
                <p><a href="{request.build_absolute_uri('/Accounts/login/')}" style="color:#38a169;">Log in to your account</a></p>
                <p>&copy; {current_year} Belco Community Credit Union</p>
            </body>
        </html>
        """

        msg = EmailMultiAlternatives(email_subject, '', settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.mixed_subtype = 'related'
        msg.attach_alternative(email_body, 'text/html')

        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Belco_logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<Belco_logo.png>')
                img.add_header('Content-Disposition', 'inline', filename='Belco_logo.png')
                msg.attach(img)

        async_send_mail(instance=msg)

        return JsonResponse({'success': True, 'message': 'Registration successful. Welcome email sent!', 'redirect_url': '/login/'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Registration failed: {str(e)}"}, status=400)

def logout_view(request):
    auth_logout(request)
    return redirect('login')

# -------------------
# Dashboard Views
# -------------------

@login_required(login_url='login')
def dashboard(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    cards = Card.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(account=request.user)
    return render(request, 'dashboard/index.html', {'account_balance': account_balance, 'cards': cards, 'transactions': transactions})

@login_required(login_url='login')
def transactions_view(request):
    transactions = Transaction.objects.filter(account=request.user)
    return render(request, 'dashboard/transactions.html', {'transactions': transactions})

@login_required(login_url='login')
def local_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/local_transfer.html', {'account_balance': account_balance, 'beneficiaries': beneficiaries})

@login_required(login_url='login')
def international_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/international_transfer.html', {'account_balance': account_balance, 'beneficiaries': beneficiaries})

@login_required(login_url='login')
def deposit_view(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    deposits = Deposit.objects.filter(account=request.user)
    return render(request, 'dashboard/deposit.html', {'account_balance': account_balance, 'deposits': deposits})

@login_required(login_url='login')
def loan_request_view(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    loans = LoanRequest.objects.filter(account=request.user)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        term = request.POST.get('term')
        try:
            loan = LoanRequest.objects.create(account=request.user, amount=Decimal(amount), term=term)
            loan.save()
            return JsonResponse({'success': True, 'message': 'Loan request submitted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return render(request, 'dashboard/loan_request.html', {'account_balance': account_balance, 'loans': loans})

@login_required(login_url='login')
def currency_swap_view(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    rates = ExchangeRate.objects.all()
    if request.method == 'POST':
        from_currency = request.POST.get('from_currency')
        to_currency = request.POST.get('to_currency')
        amount = Decimal(request.POST.get('amount'))
        rate = ExchangeRate.objects.filter(from_currency=from_currency, to_currency=to_currency).first()
        if rate:
            exchanged_amount = amount * rate.rate
            Exchange.objects.create(account=request.user, from_currency=from_currency, to_currency=to_currency, amount=amount, exchanged_amount=exchanged_amount)
            return JsonResponse({'success': True, 'exchanged_amount': exchanged_amount})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid currency pair.'}, status=400)
    return render(request, 'dashboard/currency_swap.html', {'account_balance': account_balance, 'rates': rates})

@login_required(login_url='login')
def profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone_number
        user.save()
        return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})
    return render(request, 'dashboard/profile.html')

@login_required(login_url='login')
def reset_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        user = request.user
        if not user.check_password(current_password):
            return JsonResponse({'success': False, 'message': 'Current password is incorrect.'}, status=400)
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'message': 'Passwords do not match.'}, status=400)
        user.set_password(new_password)
        user.save()
        return JsonResponse({'success': True, 'message': 'Password updated successfully.'})
    return render(request, 'dashboard/reset_password.html')
