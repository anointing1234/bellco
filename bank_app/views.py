from django.shortcuts import render,get_object_or_404, redirect
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils.html import strip_tags
from django.contrib.auth import login,authenticate
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models.signals import post_save
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_protect
import json
from django.contrib.auth.hashers import make_password,check_password
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
import os
from django.conf import settings
import requests 
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Account, AccountBalance, Card, Transaction, CurrencyBalance, Deposit, NETWORK_CHOICES, BALANCE_TYPE_CHOICES, PaymentGateway, TransferCode, Transfer, Beneficiary,ExchangeRate,Exchange,LoanRequest,ResetPassword
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from datetime import datetime
import os
import string
import random
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q 
from django.template.loader import render_to_string
import uuid
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.db import transaction
import re
import logging
from datetime import timedelta

# Configure logging
logger = logging.getLogger(__name__)





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




# authentication 

def login_view(request):
    return render(request, 'forms/login.html')  

def signup_view(request):
    return render(request, 'forms/signup.html')




def generate_unique_account_id():
    """Generate a unique 5-character alphanumeric Account ID."""
    length = 5
    characters = string.ascii_uppercase + string.digits
    while True:
        account_id = ''.join(random.choices(characters, k=length))
        if not Account.objects.filter(account_id=account_id).exists():
            return account_id

def register_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

    # Extract POST data
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    email = request.POST.get('email', '').strip()
    gender = request.POST.get('gender', '')
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')

    # Validation
    errors = []
    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")
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

    # Generate unique account_id
    account_id = generate_unique_account_id()

    try:
        # Create user
        user = Account.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            gender=gender,
            account_id=account_id
        )

        # Email content
        current_year = datetime.now().year
        email_subject = 'Welcome to Belco Community Credit Union'
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <img src="cid:Belco_logo.png" alt="Belco Community Credit Union Logo" style="width: 150px; margin-bottom: 20px;">
                <h2>Welcome, {user.first_name} {user.last_name}!</h2>
                <p>Thank you for joining Belco Community Credit Union. Your account has been successfully created.</p>
                <p><strong>Your Account ID:</strong> {user.account_id}</p>
                <p>You can now log in to manage your finances with ease, access exclusive member benefits, and enjoy personalized banking services.</p>
                <p><a href="{request.build_absolute_uri('/Accounts/login/')}" style="color: #38a169; text-decoration: none;">Log in to your account</a></p>
                <p>If you have any questions, contact our support team at support@belco.com.</p>
                <p>&copy; {current_year} Belco Community Credit Union. All Rights Reserved.</p>
            </body>
        </html>
        """

        try:
            msg = EmailMultiAlternatives(
                email_subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            msg.mixed_subtype = 'related'
            msg.attach_alternative(email_body, 'text/html')

            # Attach logo if available
            logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'images', 'Belco_logo.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<Belco_logo.png>')
                    img.add_header('Content-Disposition', 'inline', filename='Belco_logo.png')
                    msg.attach(img)
            else:
                print(f"Logo not found at: {logo_path}")

            msg.send(fail_silently=False)

        except Exception as email_error:
            print(f"Email sending failed: {str(email_error)}")
            # Continue with success response even if email fails
            return JsonResponse({
                'success': True,
                'message': 'Registration successful, but failed to send welcome email. Please contact support.',
                'redirect_url': '/login/'
            })

        return JsonResponse({
            'success': True,
            'message': 'A welcome email has been sent with your account ID.',
            'redirect_url': '/login/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Registration failed: {str(e)}"}, status=400)
    



def login_view(request):
    if request.method == 'POST':
        try:
            identifier = request.POST.get('identifier')
            password = request.POST.get('password')
            remember = request.POST.get('remember') == 'on'

            if not identifier or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Account ID and password are required.'
                }, status=400)

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
                return JsonResponse({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect_url': '/dashboard/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid account ID or password.'
                }, status=401)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred. Please try again later.'
            }, status=500)

    return render(request, 'forms/login.html')




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
    return render(request,'dashboard/transactions.html',{'transactions': transactions,})





@login_required(login_url='login') 
def local_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/local_transfer.html',{
        'account_balance': account_balance,
        'beneficiaries': beneficiaries,
        })


@login_required(login_url='login') 
def international_transfer(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'dashboard/International_Transfer.html',{
        'account_balance': account_balance,
        'beneficiaries': beneficiaries,})
   

@login_required(login_url='login')    
def loans(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    
    return render(request, 'dashboard/Loans.html',{
        'account_balance': account_balance,
        'CURRENCY_CHOICES': LoanRequest._meta.get_field('currency').choices})



@login_required(login_url='login')     
def grants(request):
    loan_requests = LoanRequest.objects.filter(user=request.user).order_by('-date')
    account_balance = AccountBalance.objects.get(account=request.user)
    return render(request, 'dashboard/Grants.html', {
        'loan_requests': loan_requests,
        'account_balance':account_balance,
        'CURRENCY_CHOICES': LoanRequest._meta.get_field('currency').choices
    })
 

@login_required(login_url='login')  
def deposit(request):
    account_balance = AccountBalance.objects.get(account=request.user)
    deposits = Deposit.objects.all()  # Fetch all deposits
    method_filter = request.GET.get('method', '')  # Get filter from query parameter
    if method_filter:
        deposits = deposits.filter(network=method_filter)  # Filter by network (assuming network is the method)
    
    context = {
        'deposits': deposits,
        'account_balance': account_balance
    }
    return render(request, 'dashboard/Deposit.html',context)



@login_required(login_url='login') 
def currency_swap(request):
    user = request.user
    account_balance = AccountBalance.objects.get(account=request.user)
    currency_balances = CurrencyBalance.objects.filter(account_balance=account_balance)
    latest_rate = ExchangeRate.objects.order_by('-updated_at').first()
    exchanges = Exchange.objects.filter(user=user).order_by('-date')
    balance_data = {}
    for cb in currency_balances:
        if cb.currency not in balance_data:
            balance_data[cb.currency] = {}
        balance_data[cb.currency][cb.balance_type] = cb.balance
    
    context = {
        'account_balance': account_balance,
        'currency_balances': balance_data,
        'latest_rate':  latest_rate,
        'exchanges': exchanges,
    }  
    return render(request, 'dashboard/Currency_Swap.html',context)




@login_required(login_url='login') 
def profile(request):
    return render(request,'dashboard/profile.html',)



def reset(request):
    return render(request,'forms/password_reset.html')



def get_payment_gateway(request):
    try:
        data = json.loads(request.body)
        currency = data.get('currency')
        if not currency:
            return JsonResponse({
                'status': 'error',
                'message': 'Currency is required'
            }, status=400)

        # Map USDT - TRC20 to USDT
        network = currency if currency != 'USDT - TRC20' else 'USDT'

        try:
            gateway = PaymentGateway.objects.get(network=network)
            qr_code_url = gateway.qr_code.url if gateway.qr_code else None
            return JsonResponse({
                'status': 'success',
                'data': {
                    'network': gateway.network,
                    'deposit_address': gateway.deposit_address,
                    'instructions': gateway.instructions or 'No instructions provided.',
                    'qr_code': qr_code_url
                }
            })
        except PaymentGateway.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'No payment gateway found for {network}'
            }, status=404)

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)


def deposit_view(request):
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['deposit_method', 'to_account', 'currency', 'amount', 'source_name']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'status': 'error',
                    'message': f'{field.replace("_", " ").title()} is required'
                }, status=400)

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount < 0.01:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Amount must be at least 0.01'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid amount format'
            }, status=400)

        # Validate terms agreement
        if not data.get('terms'):
            return JsonResponse({
                'status': 'error',
                'message': 'You must agree to the terms and conditions'
            }, status=400)

        # Map form fields to model fields
        currency = data['currency']
        network = currency if currency != 'other' else data.get('custom_currency', '').upper()
        if currency == 'other' and (not network or len(network) != 3):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid custom currency code. Please provide a 3-letter code.'
            }, status=400)
        if currency != 'other':
            network = network if network != 'USDT - TRC20' else 'USDT'

        account = data['to_account']

        # Validate network and account choices
        valid_networks = [choice[0] for choice in NETWORK_CHOICES]
        valid_accounts = [choice[0] for choice in BALANCE_TYPE_CHOICES]
        
        if network not in valid_networks and currency != 'other':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid network selected'
            }, status=400)
        
        if account not in valid_accounts:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid account type selected'
            }, status=400)

        # Create deposit record
        deposit = Deposit.objects.create(
            user=request.user,
            amount=amount,
            network=network,
            account=account,
            status='pending'
        )

        Transaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type='deposit',
            status='pending',
            to_account=account,
            institution=data.get('source_name'),
            description=f"Deposit via {data['deposit_method']}"
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Deposit request submitted successfully. Transaction ID: {deposit.TNX}'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)

def local_transfer_views(request):
    if request.method == 'POST':
        try:
            # -----------------------------
            # Extract and validate form data
            # -----------------------------
            from_account = request.POST.get('from_account')
            raw_amount = request.POST.get('amount')
            try:
                amount = Decimal(raw_amount)
            except (TypeError, ValueError, InvalidOperation):
                return JsonResponse({'success': False, 'message': 'Invalid amount'}, status=400)

            beneficiary_id = request.POST.get('beneficiary')
            account_holder = request.POST.get('account_holder')
            to_account = request.POST.get('to_account')
            bank_name = request.POST.get('bank_name')
            routing_number = request.POST.get('routing_number')
            swift_code = request.POST.get('swift_code')
            description = request.POST.get('description') or "Local transfer"
            transaction_pin = request.POST.get('transaction_pin')
            currency = request.POST.get('currency', 'USD').upper()
            bank_address = request.POST.get('bank_address') 

            user = request.user
            balance = AccountBalance.objects.get(account=user)

            # -----------------------------
            # Verify PIN
            # -----------------------------
            if hasattr(user, "pin") and str(transaction_pin) != str(user.pin):
                return JsonResponse({'success': False, 'message': 'Invalid transaction PIN'}, status=400)

            # -----------------------------
            # Balance check
            # -----------------------------
            if currency == 'USD':
                if from_account == 'checking':
                    current_balance = balance.checking_balance
                elif from_account == 'savings':
                    current_balance = balance.savings_balance
                elif from_account == 'credit':
                    current_balance = balance.credit_balance
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid account type'}, status=400)
            else:
                # For other currencies, fetch from CurrencyBalance model
                cb = CurrencyBalance.objects.filter(
                    account_balance=balance,
                    balance_type=from_account,
                    currency=currency
                ).first()

                if not cb:
                    return JsonResponse({
                        'success': False,
                        'message': f"No {currency} balance found for {from_account}"
                    }, status=400)

                current_balance = cb.balance

            if amount > current_balance:
                return JsonResponse({'success': False, 'message': 'Insufficient balance'}, status=400)

            # -----------------------------
            # Atomic transaction
            # -----------------------------
            with transaction.atomic():
                # Deduct the balance
                if currency == 'USD':
                    if from_account == 'checking':
                        balance.checking_balance -= amount
                        remaining_balance = balance.checking_balance
                    elif from_account == 'savings':
                        balance.savings_balance -= amount
                        remaining_balance = balance.savings_balance
                    elif from_account == 'credit':
                        balance.credit_balance -= amount
                        remaining_balance = balance.credit_balance
                    balance.save()
                else:
                    cb.balance -= amount
                    remaining_balance = cb.balance
                    cb.save()

                # Beneficiary
                if beneficiary_id:
                    beneficiary = Beneficiary.objects.get(id=beneficiary_id, user=user)
                else:
                    beneficiary, _ = Beneficiary.objects.get_or_create(
                        user=user,
                        full_name=account_holder or "N/A",
                        account_number=to_account or "N/A",
                        bank_name=bank_name or "N/A",
                        routing_transit_number=routing_number or "",
                        swift_code=swift_code or "",
                        bank_address=bank_address or "N/A"
                    )

                # Unique transaction reference
                unique_reference = str(uuid.uuid4())[:50]

                # Transaction record
                transaction_record = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type='transfer',
                    description=description,
                    status='pending',
                    reference=unique_reference,
                    institution=bank_name,
                    to_account=to_account,
                    from_account=getattr(user, 'account_number', 'N/A')
                )

                # Transfer record
                Transfer.objects.create(
                    user=user,
                    beneficiary=beneficiary,
                    amount=amount,
                    currency=currency,
                    reason=description,
                    status='pending',
                    remarks='Local transfer completed',
                    charge=Decimal("0.00"),
                    region='local',
                    reference=unique_reference
                )

            # -----------------------------
            # Prepare context for template & email
            # -----------------------------
            debit_context = {
                "sender_name": f"{user.first_name} {user.last_name}",
                "sender_account_number": getattr(user, "account_number", "N/A"),
                "sender_account_type": from_account,
                "receiver_name": beneficiary.full_name,
                "receiver_account_number": beneficiary.account_number,
                "receiver_bank": beneficiary.bank_name,
                "receiver_bank_address": beneficiary.bank_address,
                "transaction_reference": unique_reference,
                "transaction_date": timezone.localtime(transaction_record.transaction_date).strftime("%Y-%m-%d %H:%M:%S"),
                "region": "local",
            }

            # -----------------------------
            # Send Debit Notification Email
            # -----------------------------
            try:
                email_subject = "Debit Notification"
                email_body = render_to_string("emails/receipt_template.html", debit_context)

                msg = EmailMultiAlternatives(
                    email_subject,
                    "",  # Plain text version
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                msg.mixed_subtype = "related"
                msg.attach_alternative(email_body, "text/html")

                # Attach inline logo
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_white.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-ID', '<logo_white.png>')
                        img.add_header('Content-Disposition', 'inline', filename='logo_white.png')
                        msg.attach(img)

                msg.send(fail_silently=False)
                print("✅ Debit notification email sent.")
            except Exception as e:
                print(f"⚠️ Email not sent: {e}")

            # -----------------------------
            # Return JSON with receipt URL
            # -----------------------------
            receipt_url = reverse("transaction_receipt", args=[unique_reference])
            return JsonResponse({
                "success": True,
                "message": "Transfer successful.",
                "redirect_url": receipt_url
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Transfer failed: {str(e)}'}, status=500)

    return render(request, 'dashboard/local_transfer.html')


def internal_transfer_views(request):
    if request.method == 'POST':
        try:
            # -----------------------------
            # Extract and validate form data
            # -----------------------------
            from_account = request.POST.get('from_account')
            raw_amount = request.POST.get('amount')
            try:
                amount = Decimal(raw_amount)
            except (TypeError, ValueError, InvalidOperation):
                return JsonResponse({'success': False, 'message': 'Invalid amount'}, status=400)

            beneficiary_id = request.POST.get('beneficiary')
            account_holder = request.POST.get('account_holder')
            to_account = request.POST.get('to_account')
            bank_name = request.POST.get('bank_name')
          
            routing_number = request.POST.get('routing_number')
            swift_code = request.POST.get('swift_code')
            description = request.POST.get('description') or "International transfer"
            transaction_pin = request.POST.get('transaction_pin')
            currency = request.POST.get('currency', 'USD').upper()
            bank_address = request.POST.get('bank_address') 

            user = request.user
            balance = AccountBalance.objects.get(account=user)

            # -----------------------------
            # Verify PIN
            # -----------------------------
            if hasattr(user, "pin") and str(transaction_pin) != str(user.pin):
                return JsonResponse({'success': False, 'message': 'Invalid transaction PIN'}, status=400)

            # -----------------------------
            # Balance check
            # -----------------------------
            if currency == 'USD':
                if from_account == 'checking':
                    current_balance = balance.checking_balance
                elif from_account == 'savings':
                    current_balance = balance.savings_balance
                elif from_account == 'credit':
                    current_balance = balance.credit_balance
                else:
                    return JsonResponse({'success': False, 'message': 'Invalid account type'}, status=400)
            else:
                # For other currencies, fetch from CurrencyBalance model
                cb = CurrencyBalance.objects.filter(
                    account_balance=balance,
                    balance_type=from_account,
                    currency=currency
                ).first()

                if not cb:
                    return JsonResponse({
                        'success': False,
                        'message': f"No {currency} balance found for {from_account}"
                    }, status=400)

                current_balance = cb.balance

            if amount > current_balance:
                return JsonResponse({'success': False, 'message': 'Insufficient balance'}, status=400)

            # -----------------------------
            # Atomic transaction
            # -----------------------------
            with transaction.atomic():
                # Deduct the balance
                if currency == 'USD':
                    if from_account == 'checking':
                        balance.checking_balance -= amount
                        remaining_balance = balance.checking_balance
                    elif from_account == 'savings':
                        balance.savings_balance -= amount
                        remaining_balance = balance.savings_balance
                    elif from_account == 'credit':
                        balance.credit_balance -= amount
                        remaining_balance = balance.credit_balance
                    balance.save()
                else:
                    cb.balance -= amount
                    remaining_balance = cb.balance
                    cb.save()

                # Beneficiary
                if beneficiary_id:
                    beneficiary = Beneficiary.objects.get(id=beneficiary_id, user=user)
                else:
                    beneficiary, _ = Beneficiary.objects.get_or_create(
                        user=user,
                        full_name=account_holder or "N/A",
                        account_number=to_account or "N/A",
                        bank_name=bank_name or "N/A",
                        routing_transit_number=routing_number or "",
                        swift_code=swift_code or "",
                        bank_address=bank_address or "N/A"
                    )

                # Unique transaction reference
                unique_reference = str(uuid.uuid4())[:50]

                # Transaction record
                transaction_record = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type='transfer',
                    description=description,
                    status='pending',
                    reference=unique_reference,
                    institution=bank_name,
                    to_account=to_account,
                    from_account=getattr(user, 'account_number', 'N/A')
                )

                # Transfer record
                Transfer.objects.create(
                    user=user,
                    beneficiary=beneficiary,
                    amount=amount,
                    currency=currency,
                    reason=description,
                    status='pending',
                    remarks='International transfer completed',
                    charge=Decimal("0.00"),
                    region='wire',
                    reference=unique_reference
                )

            # -----------------------------
            # Prepare context for template & email
            # -----------------------------
            debit_context = {
                "sender_name": f"{user.first_name} {user.last_name}",
                "sender_account_number": getattr(user, "account_number", "N/A"),
                "sender_account_type": from_account,
                "receiver_name": beneficiary.full_name,
                "receiver_account_number": beneficiary.account_number,
                "receiver_bank": beneficiary.bank_name,
                "receiver_bank_address": beneficiary.bank_address,
                "transaction_reference": unique_reference,
                "transaction_date": timezone.localtime(transaction_record.transaction_date).strftime("%Y-%m-%d %H:%M:%S"),
                "region": "wire",
            }

            # -----------------------------
            # Send Debit Notification Email
            # -----------------------------
            try:
                email_subject = "Debit Notification"
                email_body = render_to_string("emails/receipt_template.html", debit_context)

                msg = EmailMultiAlternatives(
                    email_subject,
                    "",  # Plain text version
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                msg.mixed_subtype = "related"
                msg.attach_alternative(email_body, "text/html")

                # Attach inline logo
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_white.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-ID', '<logo_white.png>')
                        img.add_header('Content-Disposition', 'inline', filename='logo_white.png')
                        msg.attach(img)

                msg.send(fail_silently=False)
                print("✅ Debit notification email sent.")
            except Exception as e:
                print(f"⚠️ Email not sent: {e}")

            # -----------------------------
            # Return JSON with receipt URL
            # -----------------------------
            receipt_url = reverse("transaction_receipt", args=[unique_reference])
            return JsonResponse({
                "success": True,
                "message": "Transfer successful.",
                "redirect_url": receipt_url
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Transfer failed: {str(e)}'}, status=500)

    return render(request, 'dashboard/International_Transfer.html')




def transaction_receipt_view(request, reference):
       transaction = get_object_or_404(Transfer, reference=reference)
       beneficiary = transaction.beneficiary

       # Prepare context for the template
       context = {
           "sender_name": f"{transaction.user.first_name} {transaction.user.last_name}",
           "sender_account_number": getattr(transaction.user, "account_number", "N/A"),
           "sender_account_type": "checking" ,
           "receiver_name": beneficiary.full_name,
           "receiver_account_number": beneficiary.account_number,
           "receiver_bank": beneficiary.bank_name,
           "receiver_bank_address": beneficiary.bank_address,
           "transaction_reference": transaction.reference,
           "transaction_date": transaction.date.strftime("%Y-%m-%d %H:%M:%S"),
           "amount": transaction.amount,
           "region": transaction.region,
       }
       return render(request, "emails/receipt_template.html", context)
   


@login_required
def validate_pin(request):
    if request.method == 'POST':
        pin = request.POST.get('pin')
        if request.user.pin == pin:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Invalid PIN'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def send_transfer_code(request):
    if request.method == 'POST':
        # Delete any previous unused/unexpired codes
        TransferCode.objects.filter(user=request.user, used=False).delete()

        # Create a fresh transfer code
        transfer_code = TransferCode.objects.create(user=request.user)

        return JsonResponse({
            'success': True,
            'message': 'New transfer code generated'
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)

@login_required
def validate_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        code_type = request.POST.get('code_type')
        transfer_code = TransferCode.objects.filter(user=request.user, used=False, expires_at__gt=timezone.now()).first()
        if not transfer_code:
            return JsonResponse({'success': False, 'message': 'No valid transfer codes found'}, status=400)
        if code_type == 'tac_code' and code == transfer_code.tac_code:
            return JsonResponse({'success': True})
        if code_type == 'tax_code' and code == transfer_code.tax_code:
            return JsonResponse({'success': True})
        if code_type == 'imf_code' and code == transfer_code.imf_code:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': f'Invalid {code_type}'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)




def exchange_submit_view(request):
    if request.method == 'POST':
        user = request.user
        from_currency_field = request.POST.get('from_currency')  # e.g., "CHECKING_usd"
        to_currency_field = request.POST.get('to_currency')      # e.g., "SAVINGS_eur"
        amount = request.POST.get('amount')
        note = request.POST.get('note', '')

        # Validate inputs
        if not all([from_currency_field, to_currency_field, amount]):
            return JsonResponse({'success': False, 'error': 'All fields are required.'})

        try:
            from_balance_type, from_currency = from_currency_field.split('_')
            to_balance_type, to_currency = to_currency_field.split('_')
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid currency selection.'})

        if from_currency.lower() == to_currency.lower():
            return JsonResponse({'success': False, 'error': 'Cannot exchange the same currency.'})

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError
        except:
            return JsonResponse({'success': False, 'error': 'Invalid amount.'})

        # Get user's AccountBalance
        account_balance = get_object_or_404(AccountBalance, account=user)

        # Get user's from_currency balance
        try:
            from_balance = CurrencyBalance.objects.get(
                account_balance=account_balance,
                currency=from_currency.upper(),
                balance_type=from_balance_type.upper()  # <-- FIXED
            )
        except CurrencyBalance.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'No balance found for {from_currency.upper()} ({from_balance_type.upper()})'})

        if from_balance.balance < amount:
            return JsonResponse({'success': False, 'error': f'Insufficient balance in {from_currency.upper()} ({from_balance_type.upper()}). Please contact support to credit your account.'})

        # Get latest exchange rates
        latest_rate = ExchangeRate.objects.order_by('-updated_at').first()
        if not latest_rate:
            return JsonResponse({'success': False, 'error': 'Exchange rates are not available.'})

        # Determine the exchange rate
        rate_key = f"{from_currency.lower()}_{to_currency.lower()}"
        rate = getattr(latest_rate, rate_key, None)
        if not rate:
            return JsonResponse({'success': False, 'error': f'Exchange rate for {from_currency.upper()} → {to_currency.upper()} not found.'})

        # Calculate converted amount
        converted_amount = (amount * rate).quantize(Decimal('0.01'))

        # Perform the exchange atomically
        try:
            with transaction.atomic():
                # Deduct from from_balance
                from_balance.balance -= amount
                from_balance.save()

                # Add to to_currency balance (create if not exists)
                to_balance, created = CurrencyBalance.objects.get_or_create(
                    account_balance=account_balance,
                    currency=to_currency.upper(),
                    balance_type=to_balance_type.upper(),  # <-- FIXED
                    defaults={'balance': converted_amount}
                )
                if not created:
                    to_balance.balance += converted_amount
                    to_balance.save()

                # Record the exchange
                Exchange.objects.create(
                    user=user,
                    amount=converted_amount,
                    from_currency=from_currency.upper(),
                    to_currency=to_currency.upper(),
                    status='completed'
                )

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Exchange failed: {str(e)}'})

        return JsonResponse({
            'success': True,
            'message': f'Exchange completed: {amount} {from_currency.upper()} → {converted_amount} {to_currency.upper()}'
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})





def loan_request_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            loan_request = LoanRequest(
                user=request.user,
                amount=data['amount'],
                currency=data['currency'],
                loan_type=data['loan_type'],
                term_months=data['term_months'],
                reason=data['reason'],
                collateral=data.get('collateral')
            )
            loan_request.clean()
            loan_request.save()
            return JsonResponse({'success': True})
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred'}, status=500)
    

def account(request):
    if request.method == 'POST':
        try:
            # Handle profile picture update
            if 'profile_picture' in request.POST:  # Check if picture-form was submitted
                if 'profile_picture' not in request.FILES:  # No file uploaded
                    return JsonResponse({'error': 'Please upload a profile picture'}, status=400)
                user = request.user
                profile_picture = request.FILES['profile_picture']
                if profile_picture.size > 5 * 1024 * 1024:  # 5MB limit
                    return JsonResponse({'error': 'Profile picture must be under 5MB'}, status=400)
                user.profile_picture = profile_picture
                user.save()
                return JsonResponse({'success': True, 'message': 'Profile picture updated successfully'})
            
            # Handle profile details update
            elif 'first_name' in request.POST:
                user = request.user
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                email = request.POST.get('email', user.email)
                if email != user.email and user.__class__.objects.filter(email=email).exists():
                    return JsonResponse({'error': 'Email already in use'}, status=400)
                user.email = email
                phone_number = request.POST.get('phone_number', user.phone_number)
                if phone_number and not re.match(r'^\+?[0-9]{10,15}$', phone_number):
                    return JsonResponse({'error': 'Invalid phone number format'}, status=400)
                user.phone_number = phone_number
                user.country = request.POST.get('country', user.country)
                user.city = request.POST.get('city', user.city)
                user.gender = request.POST.get('gender', user.gender)
                user.full_clean()
                user.save()
                return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
            
            # Handle password update
            elif 'old_password' in request.POST:
                if not request.user.check_password(request.POST.get('old_password')):
                    return JsonResponse({'error': 'Current password is incorrect'}, status=400)
                if len(request.POST.get('new_password', '')) < 6:
                    return JsonResponse({'error': 'New password must be at least 6 characters'}, status=400)
                request.user.set_password(request.POST.get('new_password'))
                request.user.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Password updated successfully',
                    'redirect': reverse('login')
                })
                
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in account view: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Server error occurred'}, status=500)
    
    return render(request, 'dashboard/profile.html', {
        'user': request.user
    })


# Helper function to generate 6-digit numeric code
def generate_reset_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def password_reset_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "send_code":
            email = request.POST.get("email")
            if not email:
                return JsonResponse({"success": False, "message": "Email is required."})
            
            try:
                user = Account.objects.get(email=email)
            except Account.DoesNotExist:
                return JsonResponse({"success": False, "message": "Email not found."})
            
            # Create or update ResetPassword object
            reset_obj, created = ResetPassword.objects.get_or_create(email=email)
            reset_obj.reset_code = generate_reset_code(6)  # Generate 6-digit code
            reset_obj.expires_at = timezone.now() + timedelta(hours=24)
            reset_obj.save()
            
            # Send email with the 6-digit code
            try:
                send_mail(
                    subject="Your Password Reset Code",
                    message=f"Hello {user.username},\n\nYour password reset code is: {reset_obj.reset_code}\nIt expires in 24 hours.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                return JsonResponse({"success": False, "message": f"Failed to send email: {str(e)}"})
            
            return JsonResponse({"success": True, "message": "Reset code sent!", "email": email})
        
        elif action == "reset_password":
            email = request.POST.get("email")
            code = request.POST.get("code")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if new_password != confirm_password:
                return JsonResponse({"success": False, "message": "Passwords do not match."})

            try:
                reset_obj = ResetPassword.objects.get(email=email, reset_code=code)
            except ResetPassword.DoesNotExist:
                return JsonResponse({"success": False, "message": "Invalid reset code."})

            if not reset_obj.is_valid():
                return JsonResponse({"success": False, "message": "Reset code expired."})

            try:
                user = Account.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                reset_obj.delete()
                return JsonResponse({"success": True, "message": "Password reset successful!"})
            except Exception as e:
                return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

        return JsonResponse({"success": False, "message": "Invalid action."})
    
    return JsonResponse({"success": False, "message": "Invalid request."})



def logout_view(request):
    auth_logout(request)  # This logs out the user
    return redirect('login')
