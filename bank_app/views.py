from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.template.loader import render_to_string
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import random, string, uuid, os, threading, json, re
import logging
from email.mime.image import MIMEImage

from .models import (
    Account, AccountBalance, Card, Transaction, CurrencyBalance, Deposit, 
    NETWORK_CHOICES, BALANCE_TYPE_CHOICES, PaymentGateway, TransferCode, 
    Transfer, Beneficiary, ExchangeRate, Exchange, LoanRequest, ResetPassword
)

# ---------------------------
# Logging setup
# ---------------------------
logger = logging.getLogger(__name__)

# ---------------------------
# Helper functions
# ---------------------------

def async_send_mail(*args, **kwargs):
    """Send mail in a background thread."""
    threading.Thread(target=lambda: _send(*args, **kwargs), daemon=True).start()

def _send(*args, **kwargs):
    try:
        if 'instance' in kwargs:  
            kwargs['instance'].send(fail_silently=kwargs.get('fail_silently', False))
        else:
            send_mail(*args, **kwargs)
    except Exception as e:
        print(f"⚠️ Async email failed: {e}")

def generate_unique_account_id():
    """Generate a unique 5-character alphanumeric Account ID."""
    length = 5
    characters = string.ascii_uppercase + string.digits
    while True:
        account_id = ''.join(random.choices(characters, k=length))
        if not Account.objects.filter(account_id=account_id).exists():
            return account_id

def generate_reset_code(length=6):
    """Generate 6-digit numeric reset code."""
    return ''.join(random.choices(string.digits, k=length))

# ---------------------------
# Public pages
# ---------------------------
def home_page(request):
    return render(request,'home_page/index.html')

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
    return render(request,'home_page/Refinance-Equity copy.html')

# ---------------------------
# Authentication
# ---------------------------
def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        remember = request.POST.get('remember') == 'on'

        if not identifier or not password:
            return JsonResponse({'success': False, 'message': 'Account ID and password are required.'}, status=400)

        user = None
        try:
            account = Account.objects.filter(account_id=identifier).first()
            if account:
                user = authenticate(request, email=account.email, password=password)
            else:
                user = authenticate(request, email=identifier, password=password)
        except ObjectDoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            request.session.set_expiry(1209600 if remember else 0)
            return JsonResponse({'success': True, 'message': 'Login successful!', 'redirect_url': '/dashboard/'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid account ID or password.'}, status=401)

    return render(request, 'forms/login.html')

def signup_view(request):
    return render(request, 'forms/signup.html')

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
        errors.append("Enter a valid phone number (10-15 digits, optional leading +).")
    if not email or '@' not in email or '.' not in email:
        errors.append("Enter a valid email address.")
    if Account.objects.filter(email=email).exists():
        errors.append("This email is already registered.")
    if Account.objects.filter(phone_number=phone_number).exists():
        errors.append("This phone number is already in use.")
    if gender not in ['M', 'F', 'O']:
        errors.append("Please select a valid gender (Male, Female, Other).")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        return JsonResponse({'success': False, 'message': "\n".join(errors)}, status=400)

    account_id = generate_unique_account_id()

    try:
        user = Account.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            gender=gender,
            account_id=account_id
        )

        # Send welcome email asynchronously
        current_year = datetime.now().year
        email_subject = 'Welcome to Belco Community Credit Union'
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <img src="cid:Belco_logo.png" alt="Belco Logo" style="width:150px;margin-bottom:20px;">
                <h2>Welcome, {user.first_name} {user.last_name}!</h2>
                <p>Your Account ID: {user.account_id}</p>
                <p><a href="{request.build_absolute_uri('/Accounts/login/')}">Log in</a></p>
            </body>
        </html>
        """

        msg = EmailMultiAlternatives(
            email_subject, '', settings.DEFAULT_FROM_EMAIL, [user.email]
        )
        msg.mixed_subtype = 'related'
        msg.attach_alternative(email_body, 'text/html')

        logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'images', 'Belco_logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<Belco_logo.png>')
                img.add_header('Content-Disposition', 'inline', filename='Belco_logo.png')
                msg.attach(img)

        async_send_mail(instance=msg)

        return JsonResponse({'success': True, 'message': 'Registration successful. Check email for details.', 'redirect_url': '/login/'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=400)

def logout_view(request):
    auth_logout(request)
    return redirect('login')

# ---------------------------
# Dashboard Views
# ---------------------------

@login_required(login_url='login')
def dashboard(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    cards = Card.objects.filter(user=request.user)
    transactions = Transaction.objects.all()
    return render(request, 'dashboard/index.html', {
        'account_balance': account_balance,
        "cards": cards,
        'transactions': transactions,
    })

@login_required(login_url='login')
def transactions(request):
    transactions = Transaction.objects.all()
    return render(request,'dashboard/transactions.html',{'transactions': transactions})

@login_required(login_url='login')
def local_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/local_transfer.html', {'account_balance': account_balance, 'beneficiaries': beneficiaries})

@login_required(login_url='login')
def international_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/International_Transfer.html', {'account_balance': account_balance, 'beneficiaries': beneficiaries})

@login_required(login_url='login')
def loans(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    return render(request, 'dashboard/Loans.html', {
        'account_balance': account_balance,
        'CURRENCY_CHOICES': LoanRequest._meta.get_field('currency').choices
    })

@login_required(login_url='login')
def grants(request):
    loan_requests = LoanRequest.objects.filter(user=request.user).order_by('-date')
    account_balance = AccountBalance.objects.get(account=request.user)
    return render(request, 'dashboard/Grants.html', {
        'loan_requests': loan_requests,
        'account_balance': account_balance,
        'CURRENCY_CHOICES': LoanRequest._meta.get_field('currency').choices
    })

@login_required(login_url='login')
def deposit(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    deposits = Deposit.objects.all()
    method_filter = request.GET.get('method', '')
    if method_filter:
        deposits = deposits.filter(network=method_filter)
    return render(request, 'dashboard/Deposit.html', {'account_balance': account_balance, 'deposits': deposits})

@login_required(login_url='login')
def currency_swap(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    currency_balances = CurrencyBalance.objects.filter(account_balance=account_balance)
    latest_rate = ExchangeRate.objects.order_by('-created_at').first()
    return render(request, 'dashboard/Currency_Swap.html', {
        'account_balance': account_balance,
        'currency_balances': currency_balances,
        'latest_rate': latest_rate
    })

@login_required(login_url='login')
def profile(request):
    return render(request, 'dashboard/profile.html', {'user': request.user})

# ---------------------------
# Account Actions
# ---------------------------
@login_required(login_url='login')
def password_reset_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            return JsonResponse({'success': False, 'message': 'Incorrect old password.'}, status=400)
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'message': 'Passwords do not match.'}, status=400)

        request.user.set_password(new_password)
        request.user.save()
        return JsonResponse({'success': True, 'message': 'Password updated successfully.'})

    return render(request,'dashboard/password_reset.html')

@login_required(login_url='login')
def account_update_view(request):
    if request.method == 'POST':
        data = request.POST
        user = request.user
        errors = []

        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        phone = data.get('phone_number', user.phone_number)
        if Account.objects.exclude(pk=user.pk).filter(phone_number=phone).exists():
            errors.append('Phone number already in use.')
        else:
            user.phone_number = phone
        if errors:
            return JsonResponse({'success': False, 'message': "\n".join(errors)}, status=400)

        user.save()
        return JsonResponse({'success': True, 'message': 'Account updated successfully.'})
    return render(request, 'dashboard/account_update.html')

# ---------------------------
# Transfer/Deposit/Exchange/Loan Views (with async mail)
# ---------------------------

@login_required(login_url='login')
def transfer_submit_view(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            recipient_id = request.POST.get('recipient_account')
            sender_account_balance = AccountBalance.objects.get(account=request.user)
            recipient_account_balance = AccountBalance.objects.get(account__account_id=recipient_id)

            if sender_account_balance.balance < amount:
                return JsonResponse({'success': False, 'message': 'Insufficient funds.'}, status=400)

            with transaction.atomic():
                sender_account_balance.balance -= amount
                recipient_account_balance.balance += amount
                sender_account_balance.save()
                recipient_account_balance.save()

                txn = Transaction.objects.create(
                    sender=request.user,
                    recipient=recipient_account_balance.account,
                    amount=amount,
                    transaction_type='Transfer'
                )

                # Send email asynchronously
                subject = "Transfer Successful"
                html_body = f"Transfer of {amount} to {recipient_account_balance.account.account_id} successful."
                msg = EmailMultiAlternatives(subject, '', settings.DEFAULT_FROM_EMAIL, [request.user.email])
                msg.attach_alternative(html_body, 'text/html')
                async_send_mail(instance=msg)

            return JsonResponse({'success': True, 'message': 'Transfer completed successfully.'})
        except (ObjectDoesNotExist, InvalidOperation) as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@login_required(login_url='login')
def exchange_submit_view(request):
    if request.method == 'POST':
        try:
            from_currency = request.POST.get('from_currency')
            to_currency = request.POST.get('to_currency')
            amount = Decimal(request.POST.get('amount'))

            account_balance = AccountBalance.objects.get(account=request.user)
            if account_balance.balance < amount:
                return JsonResponse({'success': False, 'message': 'Insufficient funds.'}, status=400)

            latest_rate = ExchangeRate.objects.order_by('-created_at').first()
            converted_amount = amount * latest_rate.rate  # Simplified

            account_balance.balance -= amount
            account_balance.save()

            Exchange.objects.create(
                user=request.user,
                from_currency=from_currency,
                to_currency=to_currency,
                amount=amount,
                converted_amount=converted_amount,
                rate=latest_rate.rate
            )

            # Async email
            subject = "Currency Exchange Completed"
            html_body = f"You exchanged {amount} {from_currency} to {converted_amount} {to_currency}."
            msg = EmailMultiAlternatives(subject, '', settings.DEFAULT_FROM_EMAIL, [request.user.email])
            msg.attach_alternative(html_body, 'text/html')
            async_send_mail(instance=msg)

            return JsonResponse({'success': True, 'message': 'Exchange completed successfully.'})
        except (ObjectDoesNotExist, InvalidOperation) as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@login_required(login_url='login')
def loan_request_view(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            currency = request.POST.get('currency')
            loan = LoanRequest.objects.create(
                user=request.user,
                amount=amount,
                currency=currency,
                status='Pending'
            )

            subject = "Loan Request Submitted"
            html_body = f"Your loan request of {amount} {currency} has been submitted."
            msg = EmailMultiAlternatives(subject, '', settings.DEFAULT_FROM_EMAIL, [request.user.email])
            msg.attach_alternative(html_body, 'text/html')
            async_send_mail(instance=msg)

            return JsonResponse({'success': True, 'message': 'Loan request submitted successfully.'})
        except InvalidOperation as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@login_required(login_url='login')
def deposit_submit_view(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            network = request.POST.get('network')
            account_balance = AccountBalance.objects.get(account=request.user)

            Deposit.objects.create(user=request.user, amount=amount, network=network)
            account_balance.balance += amount
            account_balance.save()

            # Async email
            subject = "Deposit Successful"
            html_body = f"Your deposit of {amount} via {network} has been processed successfully."
            msg = EmailMultiAlternatives(subject, '', settings.DEFAULT_FROM_EMAIL, [request.user.email])
            msg.attach_alternative(html_body, 'text/html')
            async_send_mail(instance=msg)

            return JsonResponse({'success': True, 'message': 'Deposit completed successfully.'})
        except InvalidOperation as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)
