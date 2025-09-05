from django.contrib import admin,messages
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import GroupAdmin as DefaultGroupAdmin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Account, AccountBalance, CurrencyBalance, Card, LoanRequest, Exchange,
    ResetPassword, TransferCode, Transaction, Deposit, PaymentGateway,
    Beneficiary, Transfer, ExchangeRate,BALANCE_TYPE_CHOICES
)
from django.utils.html import format_html
from django.templatetags.static import static
from django.contrib.auth.hashers import make_password
from django import forms
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from datetime import datetime
import os
from django.conf import settings
from .utils import generate_unique_account_id
from django.db import transaction
from django.utils import timezone
import uuid


# Unregister the default Group admin to avoid AlreadyRegistered error
admin.site.unregister(Group)


class AccountCreationAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = Account
        fields = ['email', 'username', 'first_name', 'last_name', 'phone_number', 'gender', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        phone_number = cleaned_data.get("phone_number")
        email = cleaned_data.get("email")
        gender = cleaned_data.get("gender")

        errors = []
        if not cleaned_data.get("first_name"):
            errors.append("First name is required.")
        if not cleaned_data.get("last_name"):
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
            raise forms.ValidationError(errors)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data["password"])
        user.account_id = generate_unique_account_id()
        if commit:
            user.save()

            # --- Create balances here ---
            account_balance = AccountBalance.objects.create(account=user)
            
            for currency in ['GBP', 'EUR']:
                for balance_type in BALANCE_TYPE_CHOICES:
                    CurrencyBalance.objects.create(
                        account_balance=account_balance,
                        currency=currency,
                        balance_type=balance_type[0],
                        balance=0.00
                    )

            # --- Create default debit card for non-admin ---
            if not (user.is_staff or user.is_superuser):
                Card.objects.create(
                    user=user,
                    card_type='debit',
                    vendor='visa',
                    status='pending',
                    balance_type='CHECKING'
                )

            self.send_welcome_email(user)
        return user


    def send_welcome_email(self, user):
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
                <p><a href="{settings.SITE_URL}/Accounts/login/" style="color: #38a169; text-decoration: none;">Log in to your account</a></p>
                <p>If you have any questions, contact our support team at support@belco.com.</p>
                <p>&copy; {current_year} Belco Community Credit Union. All Rights Reserved.</p>
            </body>
        </html>
        """
        try:
            msg = EmailMultiAlternatives(email_subject, '', settings.DEFAULT_FROM_EMAIL, [user.email])
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
            msg.send(fail_silently=False)
        except Exception as e:
            print(f"Email sending failed: {e}")

class CardInline(TabularInline):
    model = Card
    extra = 0
    fields = ['card_type', 'vendor', 'get_masked_card_number', 'status', 'balance_type', 'expiry_date']
    readonly_fields = ['get_masked_card_number']
    
    def get_masked_card_number(self, obj):
        return f"****-****-****-{obj.account[-4:]}" if obj.account else "N/A"
    get_masked_card_number.short_description = "Card Number"

class CurrencyBalanceInline(TabularInline):
    model = CurrencyBalance
    extra = 0
    fields = ['currency', 'balance_type', 'balance']
    readonly_fields = ['currency', 'balance_type']

class AccountBalanceInline(TabularInline):
    model = AccountBalance
    extra = 0
    fields = ['checking_balance', 'savings_balance', 'credit_balance']
    readonly_fields = ['checking_balance', 'savings_balance', 'credit_balance']



@admin.register(Account)
class AccountAdmin(ModelAdmin):
    form =  AccountCreationAdminForm  # Use this form for creation

    list_display = ['account_id','email', 'username', 'first_name', 'last_name', 
                    'is_staff', 'is_superuser', 'date_joined', 'profile_pic_preview']
    list_filter = ['is_staff', 'is_superuser', 'country', 'gender']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'account_id']
    readonly_fields = ['cot_code', 'tax_code', 'imf_code', 'account_number', 'pin', 'date_joined', 'last_login']
    list_display_links = ['email', 'username']
    ordering = ['-date_joined']
    autocomplete_fields = ['groups', 'user_permissions']  

    inlines = [AccountBalanceInline, CardInline]

    def profile_pic_preview(self, obj):
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return format_html('<img src="{}" width="40" height="40" style="border-radius:50%;" />', obj.profile_picture.url)
        return format_html('<img src="{}" width="40" height="40" style="border-radius:50%;" />', static('assets/images/avatar/default_profile.png'))



@admin.register(AccountBalance)
class AccountBalanceAdmin(ModelAdmin):
    list_display = ['account', 'checking_balance', 'savings_balance', 'credit_balance']
    list_editable = ['checking_balance', 'savings_balance', 'credit_balance']  # ✅ balances editable in list view
    search_fields = ['account__email', 'account__username']
    inlines = [CurrencyBalanceInline]
    list_per_page = 25
    autocomplete_fields = ['account']

    def save_model(self, request, obj, form, change):
        balance_changes = {}

        if change:  # Editing existing record
            old_obj = AccountBalance.objects.get(pk=obj.pk)

            if obj.checking_balance != old_obj.checking_balance:
                balance_changes['CHECKING'] = obj.checking_balance - old_obj.checking_balance
            if obj.savings_balance != old_obj.savings_balance:
                balance_changes['SAVINGS'] = obj.savings_balance - old_obj.savings_balance
            if obj.credit_balance != old_obj.credit_balance:
                balance_changes['CREDIT'] = obj.credit_balance - old_obj.credit_balance
        else:
            # New record
            if obj.checking_balance > 0:
                balance_changes['CHECKING'] = obj.checking_balance
            if obj.savings_balance > 0:
                balance_changes['SAVINGS'] = obj.savings_balance
            if obj.credit_balance > 0:
                balance_changes['CREDIT'] = obj.credit_balance

        # Save object AFTER tracking changes
        super().save_model(request, obj, form, change)

        # Create Deposit & Transaction for positive changes
        for account_type, change_amount in balance_changes.items():
            if change_amount > 0:
                Deposit.objects.create(
                    user=obj.account,
                    amount=change_amount,
                    account=account_type,
                    status="completed",
                    date=timezone.now()
                )

                Transaction.objects.create(
                    user=obj.account,
                    amount=change_amount,
                    transaction_type="deposit",
                    description=f"Admin deposit to {account_type} balance",
                    status="completed",
                    transaction_date=timezone.now(),
                    to_account=str(obj.account.id)
                )

    def save_related(self, request, form, formsets, change):
        """
        Ensures balance changes done in list_editable also trigger deposits/transactions.
        """
        super().save_related(request, form, formsets, change)
        self.save_model(request, form.instance, form, change)


@admin.register(CurrencyBalance)
class CurrencyBalanceAdmin(ModelAdmin):
    list_display = ['get_user_email', 'currency', 'balance_type', 'balance']
    list_editable = ['balance']  # ✅ balance editable directly
    list_filter = ['currency', 'balance_type']
    search_fields = ['account_balance__account__email', 'account_balance__account__username']
    list_per_page = 25
    autocomplete_fields = ['account_balance']

    def get_user_email(self, obj):
        return obj.account_balance.account.email
    get_user_email.short_description = "User Email"

    def save_model(self, request, obj, form, change):
        balance_change = None

        if change:  # Editing existing record
            old_obj = CurrencyBalance.objects.get(pk=obj.pk)
            if obj.balance != old_obj.balance:
                balance_change = obj.balance - old_obj.balance
        else:
            # New record
            if obj.balance > 0:
                balance_change = obj.balance

        # Save object AFTER tracking changes
        super().save_model(request, obj, form, change)

        # If balance increased, create Deposit & Transaction
        if balance_change and balance_change > 0:
            Deposit.objects.create(
                user=obj.account_balance.account,
                amount=balance_change,
                account=obj.balance_type,
                status="completed",
                date=timezone.now()
            )

            Transaction.objects.create(
                user=obj.account_balance.account,
                amount=balance_change,
                transaction_type="deposit",
                description=f"Admin deposit to {obj.currency} {obj.balance_type} balance",
                status="completed",
                transaction_date=timezone.now(),
                to_account=str(obj.account_balance.account.id)
            )

    def save_related(self, request, form, formsets, change):
        """
        Ensures balance changes done in list_editable also trigger deposits/transactions.
        """
        super().save_related(request, form, formsets, change)
        self.save_model(request, form.instance, form, change)


@admin.register(Card)
class CardAdmin(ModelAdmin):
    list_display = ['user', 'card_type', 'vendor', 'get_masked_card_number', 'status', 'balance_type', 'expiry_date']
    list_filter = ['card_type', 'vendor', 'status', 'balance_type']
    search_fields = ['user__email', 'account']
    readonly_fields = ['account', 'card_password', 'get_masked_card_number']
    list_per_page = 25
    autocomplete_fields = ['user']
    
    def get_masked_card_number(self, obj):
        return f"****-****-****-{obj.account[-4:]}" if obj.account else "N/A"
    get_masked_card_number.short_description = "Card Number"


@admin.register(LoanRequest)
class LoanRequestAdmin(ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'loan_type', 'status', 'date']
    list_filter = ['status', 'currency', 'loan_type']
    search_fields = ['user__email', 'reason', 'status_detail']
    readonly_fields = ['date']
    list_per_page = 25
    autocomplete_fields = ['user', 'approved_by']

    actions = ['approve_loans', 'decline_loans']

    @admin.action(description="Approve selected loan requests")
    def approve_loans(self, request, queryset):
        for loan in queryset:
            if loan.status != "pending":
                self.message_user(
                    request,
                    f"Loan {loan.id} is not pending.",
                    level=messages.WARNING
                )
                continue

            try:
                with transaction.atomic():
                    # Update loan status
                    loan.status = "approved"
                    loan.approved_by = request.user
                    loan.save()

                    # Update account balance
                    account_balance, _ = AccountBalance.objects.get_or_create(account=loan.user)

                    if loan.currency == "USD":
                        # Increase credit balance in AccountBalance
                        account_balance.credit_balance += loan.amount
                        account_balance.save()
                    else:
                        # Handle non-USD loans via CurrencyBalance
                        currency_balance, _ = CurrencyBalance.objects.get_or_create(
                            account_balance=account_balance,
                            currency=loan.currency,
                            balance_type="CREDIT"
                        )
                        currency_balance.balance += loan.amount
                        currency_balance.save()

                    self.message_user(
                        request,
                        f"Loan of {loan.amount} {loan.currency} for {loan.user.email} approved and credited.",
                        level=messages.SUCCESS
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error approving loan {loan.id}: {str(e)}",
                    level=messages.ERROR
                )

    @admin.action(description="Decline selected loan requests")
    def decline_loans(self, request, queryset):
        for loan in queryset:
            if loan.status != "pending":
                self.message_user(
                    request,
                    f"Loan {loan.id} is not pending.",
                    level=messages.WARNING
                )
                continue

            try:
                loan.status = "declined"
                loan.approved_by = request.user
                loan.save()

                self.message_user(
                    request,
                    f"Loan of {loan.amount} {loan.currency} for {loan.user.email} declined.",
                    level=messages.INFO
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error declining loan {loan.id}: {str(e)}",
                    level=messages.ERROR
                )


@admin.register(Exchange)
class ExchangeAdmin(ModelAdmin):
    list_display = ['user', 'amount', 'from_currency', 'to_currency', 'status', 'date']
    list_filter = ['from_currency', 'to_currency', 'status']
    search_fields = ['user__email']
    readonly_fields = ['date']
    list_per_page = 25
    autocomplete_fields = ['user']

@admin.register(ResetPassword)
class ResetPasswordAdmin(ModelAdmin):
    list_display = ['email', 'reset_code', 'created_at', 'expires_at', 'is_valid']
    search_fields = ['email']
    readonly_fields = ['reset_code', 'created_at', 'expires_at']
    list_filter = ['created_at']
    list_per_page = 25

@admin.register(TransferCode)
class TransferCodeAdmin(ModelAdmin):
    list_display = ['user', 'tac_code', 'tax_code', 'imf_code', 'created_at', 'is_valid']
    search_fields = ['user__email', 'tac_code', 'tax_code', 'imf_code']
    list_filter = ['used', 'created_at']
    readonly_fields = ['tac_code', 'tax_code', 'imf_code', 'created_at', 'expires_at']
    list_per_page = 25
    autocomplete_fields = ['user']

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'status', 'transaction_date']
    list_filter = ['transaction_type', 'status', 'region']
    search_fields = ['user__email', 'reference', 'description']
    readonly_fields = ['reference']
    list_per_page = 25
    autocomplete_fields = ['user']



@admin.register(Deposit)
class DepositAdmin(ModelAdmin):
    list_display = ['user', 'amount', 'account', 'network', 'status', 'date']
    list_editable = ['amount', 'status','date']  # ✅ Make amount & status editable
    list_filter = ['account', 'network', 'status']
    search_fields = ['user__email', 'TNX']
    readonly_fields = ['TNX']
    list_per_page = 25
    autocomplete_fields = ['user']
    actions = ['approve_deposit']

    def approve_deposit(self, request, queryset):
        for deposit in queryset:
            if deposit.status == 'pending':
                try:
                    with transaction.atomic():
                        # Get or create AccountBalance
                        account_balance, _ = AccountBalance.objects.get_or_create(account=deposit.user)
                        
                        # Update balance based on account type and currency
                        if deposit.account in ['CHECKING', 'SAVINGS', 'CREDIT']:
                            balance_field = f"{deposit.account.lower()}_balance"
                            setattr(account_balance, balance_field, getattr(account_balance, balance_field) + deposit.amount)
                            account_balance.save()
                        else:
                            # Update CurrencyBalance for non-USD currencies
                            currency_balance, _ = CurrencyBalance.objects.get_or_create(
                                account_balance=account_balance,
                                currency=deposit.account,
                                balance_type='CHECKING'
                            )
                            currency_balance.balance += deposit.amount
                            currency_balance.save()

                        # Update deposit status
                        deposit.status = 'completed'
                        deposit.save()

                        # Get or create transaction
                        transaction_obj = Transaction.objects.filter(
                            user=deposit.user,
                            amount=deposit.amount,
                            transaction_type='deposit',
                            to_account=deposit.account,
                            status='pending'
                        ).first()
                        
                        if not transaction_obj:
                            # Create new transaction if none exists
                            transaction_obj = Transaction.objects.create(
                                user=deposit.user,
                                amount=deposit.amount,
                                transaction_type='deposit',
                                to_account=deposit.account,
                                status='completed',
                                description=f"Deposit via {deposit.network}",
                                reference=deposit.TNX if deposit.TNX else str(uuid.uuid4())[:50]
                            )
                        else:
                            # Update existing transaction
                            transaction_obj.status = 'completed'
                            transaction_obj.save()

                        self.message_user(
                            request,
                            f"✅ Deposit of {deposit.amount} {deposit.account} approved for {deposit.user}",
                            messages.SUCCESS
                        )
                except Exception as e:
                    self.message_user(
                        request,
                        f"❌ Error approving deposit for {deposit.user}: {str(e)}",
                        messages.ERROR
                    )
            else:
                self.message_user(
                    request,
                    f"⚠️ Deposit for {deposit.user} is not pending",
                    messages.WARNING
                )

    approve_deposit.short_description = "Approve selected deposits"

@admin.register(PaymentGateway)
class PaymentGatewayAdmin(ModelAdmin):
    list_display = ['network', 'deposit_address', 'qr_code']
    search_fields = ['network', 'deposit_address']
    readonly_fields = ['qr_code']
    list_per_page = 25

@admin.register(Beneficiary)
class BeneficiaryAdmin(ModelAdmin):
    list_display = ['user', 'full_name', 'bank_name', 'account_number', 'created_at']
    search_fields = ['user__email', 'full_name', 'bank_name', 'account_number']
    list_filter = ['bank_name', 'created_at']
    list_per_page = 25
    autocomplete_fields = ['user']



@admin.register(Transfer)
class TransferAdmin(ModelAdmin):
    list_display = ['user', 'beneficiary', 'amount', 'currency', 'status', 'date']
    list_editable = ['amount', 'status','date']  # ✅ Make amount & status editable
    list_filter = ['currency', 'status', 'region']
    search_fields = ['user__email', 'beneficiary__full_name', 'reference']
    readonly_fields = ['reference']
    list_per_page = 25
    autocomplete_fields = ['user', 'beneficiary']
    actions = ['approve_transfer', 'decline_transfer']

    def approve_transfer(self, request, queryset):
        for transfer in queryset:
            if transfer.status != 'pending':
                self.message_user(request, f"Transfer {transfer.reference} is not pending", messages.WARNING)
                continue

            try:
                with transaction.atomic():
                    # Approve transfer
                    transfer.status = 'completed'
                    transfer.save()

                    # Match transaction by reference
                    txn = Transaction.objects.filter(reference=transfer.reference, status='pending').first()
                    if txn:
                        txn.status = 'completed'
                        txn.save()
                        self.message_user(
                            request,
                            f"✅ Transfer {transfer.reference} approved and transaction updated",
                            messages.SUCCESS
                        )
                    else:
                        self.message_user(
                            request,
                            f"⚠️ Transfer {transfer.reference} approved but no matching transaction found",
                            messages.WARNING
                        )
            except Exception as e:
                self.message_user(request, f"❌ Error approving transfer {transfer.reference}: {str(e)}", messages.ERROR)

    approve_transfer.short_description = "Approve selected transfers"

    def decline_transfer(self, request, queryset):
        for transfer in queryset:
            if transfer.status != 'pending':
                self.message_user(request, f"Transfer {transfer.reference} is not pending", messages.WARNING)
                continue

            try:
                with transaction.atomic():
                    # Decline transfer
                    transfer.status = 'failed'
                    transfer.save()

                    # Match transaction by reference
                    txn = Transaction.objects.filter(reference=transfer.reference, status='pending').first()
                    if txn:
                        txn.status = 'failed'
                        txn.save()
                        self.message_user(
                            request,
                            f"❌ Transfer {transfer.reference} declined and transaction updated",
                            messages.ERROR
                        )
                    else:
                        self.message_user(
                            request,
                            f"⚠️ Transfer {transfer.reference} declined but no matching transaction found",
                            messages.WARNING
                        )
            except Exception as e:
                self.message_user(request, f"❌ Error declining transfer {transfer.reference}: {str(e)}", messages.ERROR)

    decline_transfer.short_description = "Decline selected transfers"


@admin.register(ExchangeRate)
class ExchangeRateAdmin(ModelAdmin):
    list_display = ['eur_usd', 'gbp_usd', 'eur_gbp', 'updated_at']
    search_fields = ['eur_usd', 'gbp_usd', 'eur_gbp']
    readonly_fields = ['updated_at']
    list_filter = ['updated_at']
    list_per_page = 25

@admin.register(Group)
class GroupAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 25

@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ['name', 'codename']
    search_fields = ['name', 'codename']
    list_filter = ['content_type']
    list_per_page = 25
