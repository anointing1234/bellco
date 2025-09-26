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
    password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'vTextField',  # Django admin default style
                'style': 'width: 300px; background-color: #1e1e1e; color: #fff; border: 1px solid #555; padding: 5px; border-radius: 3px;',
                'autocomplete': 'new-password'
            }
        )
    )

    confirm_password = forms.CharField(
        label="Confirm Password",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'vTextField',  
                'style': 'width: 300px; background-color: #1e1e1e; color: #fff; border: 1px solid #555; padding: 5px; border-radius: 3px;',
                'autocomplete': 'new-password'
            }
        )
    )



    class Meta:
        model = Account
        fields = [
            'email', 'username', 'first_name', 'last_name', 'phone_number',
            'gender', 'city', 'country', 'pin'
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = Account.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already registered.")
        if not email or '@' not in email or '.' not in email:
            raise forms.ValidationError("Enter a valid email address.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        qs = Account.objects.filter(phone_number=phone_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This phone number is already in use.")
        if not phone_number or not (10 <= len(phone_number.replace('+', '')) <= 15 and phone_number.replace('+', '').isdigit()):
            raise forms.ValidationError("Enter a valid phone number (10-15 digits, optional leading +).")
        return phone_number

    def clean_gender(self):
        gender = self.cleaned_data.get("gender")
        if gender not in ['M', 'F', 'O', '']:
            raise forms.ValidationError("Please select a valid gender (Male, Female, Other, Prefer not to say).")
        return gender

    def clean_pin(self):
        pin = self.cleaned_data.get("pin")
        if pin and (not pin.isdigit() or len(pin) != 4):
            raise forms.ValidationError("PIN must be 4 digits.")
        return pin

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password:
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

        if not cleaned_data.get("first_name"):
            raise forms.ValidationError("First name is required.")
        if not cleaned_data.get("last_name"):
            raise forms.ValidationError("Last name is required.")
        if not cleaned_data.get("country"):
            raise forms.ValidationError("Country is required.")
        if not cleaned_data.get("city"):
            raise forms.ValidationError("City is required.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.password = make_password(password)
        if not user.pin:
            user.pin = self.cleaned_data.get("pin") or user.generate_unique_digits("pin", 4)
        if not self.instance.pk:
            # New account creation logic
            user.account_id = generate_unique_account_id()
        if commit:
            user.save()

            if not self.instance.pk:
                # Create balances
                account_balance = AccountBalance.objects.create(account=user)
                for currency in ['GBP', 'EUR']:
                    for balance_type in BALANCE_TYPE_CHOICES:
                        CurrencyBalance.objects.create(
                            account_balance=account_balance,
                            currency=currency,
                            balance_type=balance_type[0],
                            balance=0.00
                        )

                # Create default debit card for non-admins
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
                <img src="cid:Belco_logo.png" alt="Belco Logo" style="width: 150px; margin-bottom: 20px;">
                <h2>Welcome, {user.first_name} {user.last_name}!</h2>
                <p>Your account has been successfully created.</p>
                <p><strong>Your Account ID:</strong> {user.account_id}</p>
                <p><a href="{settings.SITE_URL}/Accounts/login/" style="color: #38a169;">Log in to your account</a></p>
                <p>&copy; {current_year} Belco Community Credit Union</p>
            </body>
        </html>
        """
        try:
            msg = EmailMultiAlternatives(email_subject, '', settings.DEFAULT_FROM_EMAIL, [user.email])
            msg.mixed_subtype = 'related'
            msg.attach_alternative(email_body, 'text/html')

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
    form = AccountCreationAdminForm

    list_display = [
        'profile_pic_preview',  # moved to first
        'account_id',
        'email',
        'username',
        'is_active',
        'is_superuser',
        'date_joined',
    ]

    list_filter = ['is_staff', 'is_superuser', 'country', 'gender','two_factor_enabled']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'account_id']
    readonly_fields = ['account_number','last_login']
    list_display_links = ['email', 'username']
    ordering = ['-date_joined']
    autocomplete_fields = ['groups', 'user_permissions']

    inlines = [AccountBalanceInline, CardInline]

    fieldsets = (
        (None, {
            'fields': (
                'email', 'username', 'first_name', 'last_name',
                'profile_picture', 'password', 'confirm_password',
                'country', 'city','gender',
            )
        }),
        # ('Permissions', {
        #     'fields': ('is_active', 'is_staff', 'is_superuser')
        # }),
        ('Important Dates', {
            'fields': ('last_login','date_joined',)  # now editable
        }),
        ('Two Factor', {
            'fields': ('two_factor_enabled',)
        }),
        ('Account Info', {
            'fields': ('account_number', 'pin')
        }),
    )


    def profile_pic_preview(self, obj):
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%;" />',
                obj.profile_picture.url
            )
        return format_html(
            '<img src="{}" width="40" height="40" style="border-radius:50%;" />',
            static('assets/images/avatar/default_profile.png')
        )
    profile_pic_preview.short_description = "Profile Picture"


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



# Define choices at module level (as provided in your model)
CURRENCY_CHOICES = (
    ('USD', 'US Dollar'),
    ('GBP', 'British Pound'),
    ('EUR', 'Euro'),
)

BALANCE_TYPE_CHOICES = (
    ('CHECKING', 'Checking'),
    ('SAVINGS', 'Savings'),
    ('CREDIT', 'Credit'),
)

@admin.register(CurrencyBalance)
class CurrencyBalanceAdmin(ModelAdmin):
    list_display = ['get_user_email', 'get_username', 'currency_display', 'balance_type_display', 'balance', 'formatted_balance']
    list_editable = ['balance']  # Allow direct editing of balance
    list_filter = ['currency', 'balance_type', 'account_balance__account__is_active']
    search_fields = ['account_balance__account__email', 'account_balance__account__username']
    list_per_page = 25
    autocomplete_fields = ['account_balance']
    list_select_related = ['account_balance__account']  # Optimize queries
    ordering = ['account_balance__account__email', 'currency', 'balance_type']
    actions = ['reset_balance']  # Add action to reset balance

    def get_user_email(self, obj):
        """Display user's email."""
        return obj.account_balance.account.email
    get_user_email.short_description = "User Email"

    def get_username(self, obj):
        """Display user's username."""
        return obj.account_balance.account.username
    get_username.short_description = "Username"

    def currency_display(self, obj):
        """Display full currency name."""
        return dict(CURRENCY_CHOICES).get(obj.currency, obj.currency)
    currency_display.short_description = "Currency"

    def balance_type_display(self, obj):
        """Display full balance type name."""
        return dict(BALANCE_TYPE_CHOICES).get(obj.balance_type, obj.balance_type)
    balance_type_display.short_description = "Account Type"

    def formatted_balance(self, obj):
        """Display balance with currency formatting."""
        return f"{obj.balance:,.2f} {obj.currency}"
    formatted_balance.short_description = "Formatted Balance"

    def reset_balance(self, request, queryset):
        """Action to reset selected balances to 0."""
        for obj in queryset:
            if obj.balance != 0:
                with transaction.atomic():
                    balance_change = -obj.balance
                    obj.balance = 0
                    obj.save()
                    # Log as a withdrawal if balance was positive
                    if balance_change < 0:
                        Transaction.objects.create(
                            user=obj.account_balance.account,
                            amount=-balance_change,
                            transaction_type="withdrawal",
                            description=f"Admin Reset {obj.currency} {obj.balance_type} Balance",
                            status="completed",
                            transaction_date=timezone.now(),
                            to_account=str(obj.account_balance.account.id)
                        )
        self.message_user(request, f"Successfully reset {queryset.count()} balance(s).", level=messages.SUCCESS)
    reset_balance.short_description = "Reset selected balances to 0"

    def save_model(self, request, obj, form, change):
        """Handle balance changes and create related Deposit/Transaction records."""
        try:
            with transaction.atomic():
                balance_change = None
                if change:  # Editing existing record
                    old_obj = CurrencyBalance.objects.select_related('account_balance__account').get(pk=obj.pk)
                    if obj.balance != old_obj.balance:
                        balance_change = obj.balance - old_obj.balance
                else:  # New record
                    if obj.balance > 0:
                        balance_change = obj.balance

                # Validate balance
                if obj.balance < 0:
                    self.message_user(request, "Balance cannot be negative.", level=messages.ERROR)
                    return

                # Save the object
                super().save_model(request, obj, form, change)

                # Create Deposit and Transaction for positive balance changes
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
                        description=f"Admin Deposit to {obj.currency} {obj.balance_type} Balance",
                        status="completed",
                        transaction_date=timezone.now(),
                        to_account=str(obj.account_balance.account.id)
                    )
                elif balance_change and balance_change < 0:
                    # Log negative balance changes as withdrawals
                    Transaction.objects.create(
                        user=obj.account_balance.account,
                        amount=-balance_change,
                        transaction_type="withdrawal",
                        description=f"Admin Adjustment to {obj.currency} {obj.balance_type} Balance",
                        status="completed",
                        transaction_date=timezone.now(),
                        to_account=str(obj.account_balance.account.id)
                    )

        except Exception as e:
            self.message_user(request, f"Error saving balance: {str(e)}", level=messages.ERROR)

    def save_related(self, request, form, formsets, change):
        """Ensure list_editable balance changes trigger deposits/transactions."""
        super().save_related(request, form, formsets, change)
        self.save_model(request, form.instance, form, change)

    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related('account_balance__account')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add balance change history to change view."""
        extra_context = extra_context or {}
        if object_id:
            balance = CurrencyBalance.objects.get(pk=object_id)
            deposits = Deposit.objects.filter(
                user=balance.account_balance.account,
                account=balance.balance_type
            ).order_by('-date')[:5]
            transactions = Transaction.objects.filter(
                user=balance.account_balance.account,
                to_account=str(balance.account_balance.account.id),
                transaction_type__in=['deposit', 'withdrawal']
            ).order_by('-transaction_date')[:5]
            extra_context.update({
                'recent_deposits': deposits,
                'recent_transactions': transactions,
            })
        return super().change_view(request, object_id, form_url, extra_context)


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