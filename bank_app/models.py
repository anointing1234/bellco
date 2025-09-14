from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from datetime import date, timedelta
import uuid
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from django.core.validators import MinValueValidator, MaxValueValidator

# Shared choices
STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
)

LOAN_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('declined', 'Declined'),
)

TRANSACTION_TYPE_CHOICES = (
    ('deposit', 'Deposit'),
    ('withdrawal', 'Withdrawal'),
    ('transfer', 'Transfer'),
    ('payment', 'Payment'),
)

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

NETWORK_CHOICES = (
    ('Ethereum', 'Ethereum'),
    ('Bitcoin', 'Bitcoin'),
    ('USDT', 'USDT'),
)

class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email.split('@')[0])

        first_name = extra_fields.pop('first_name', '')
        last_name = extra_fields.pop('last_name', '')
        phone_number = extra_fields.pop('phone_number', '')

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        
        
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email=email, password=password, **extra_fields)



GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
    ('', 'Prefer not to say'),
)

class Account(AbstractBaseUser, PermissionsMixin):
    account_id = models.CharField(max_length=8, unique=True, blank=True, null=True)
    email = models.EmailField(verbose_name="Email", max_length=100, unique=True)
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(r'^\+?[0-9]{10,15}$', 'Enter a valid phone number.')]
    )
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    security_code = models.IntegerField(
            blank=True,
            null=True,
            validators=[
                MinValueValidator(100000, message='Security code must be at least 100000.'),
                MaxValueValidator(999999, message='Security code must be at most 999999.')
            ]
        )
    

    two_factor_enabled = models.BooleanField(default=False)
    account_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    date_joined = models.DateTimeField(verbose_name="Date Joined",blank=True, null=True)
    last_login = models.DateTimeField(verbose_name="Last Login", auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    pin = models.CharField(max_length=6, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        default='profile_pics/default_profile.png',
        blank=True,
        null=True,
        help_text="Profile picture (min 300x300, max 5MB, GIFs allowed)."
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = AccountManager()

    def __str__(self):
        return self.email
    

    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email

    def generate_username(self):
        base_username = self.email.split('@')[0]
        username = base_username
        counter = 1
        while Account.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username
    
    def generate_random_digits(self, length=8):
        return ''.join(random.choices(string.digits, k=length))

    def generate_unique_digits(self, field_name, length=8):
        code = self.generate_random_digits(length)
        while Account.objects.filter(**{field_name: code}).exists():
            code = self.generate_random_digits(length)
        return code

    def save(self, *args, **kwargs):
        if not self.account_number:
            # Generate only digits for account number
            self.account_number = self.generate_unique_digits("account_number", 10)

        if not self.username:
            self.username = self.generate_username()

        # Removed auto-generation for cot_code, tax_code, and imf_code

        if not self.pin:
            # Generate only 4-digit numeric PIN
            self.pin = self.generate_unique_digits("pin", 4)

        super().save(*args, **kwargs)


class AccountBalance(models.Model):
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_balance'
    )
    checking_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Checking account balance in USD."
    )
    savings_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Savings account balance in USD."
    )
    credit_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Outstanding credit balance in USD."
    )

    
    def total_balance(self):
        return self.checking_balance + self.savings_balance - self.credit_balance


    def __str__(self):
        return f"USD Balances for {self.account.email}: Checking=${self.checking_balance}, Savings=${self.savings_balance}, Credit=${self.credit_balance}"

class CurrencyBalance(models.Model):
    account_balance = models.ForeignKey(
        AccountBalance,
        on_delete=models.CASCADE,
        related_name='currency_balances'
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    balance_type = models.CharField(max_length=10, choices=BALANCE_TYPE_CHOICES)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Balance for the specified currency and account type."
    )

    class Meta:
        unique_together = ('account_balance', 'currency', 'balance_type')

    def __str__(self):
        return f"{self.currency} {self.balance_type} Balance for {self.account_balance.account.email}: {self.balance}"

def default_expiry_date():
    return date.today() + timedelta(days=730)

CARD_TYPE_CHOICES = (
    ('credit', 'Credit'),
    ('debit', 'Debit'),
    ('prepaid', 'Prepaid'),
)

VENDOR_CHOICES = (
    ('visa', 'Visa'),
    ('mastercard', 'MasterCard'),
    ('amex', 'American Express'),
    ('discover', 'Discover'),
)

class Card(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cards'
    )
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, default='debit')
    vendor = models.CharField(max_length=20, choices=VENDOR_CHOICES, default='mastercard')
    account = models.CharField(max_length=16, unique=True, blank=True, null=True, help_text="16-digit card number")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    card_password = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="4-digit PIN for the card (store securely in production)"
    )
    expiry_date = models.DateField(
        default=default_expiry_date,
        help_text="Expiry date (2 years from creation)"
    )
    balance_type = models.CharField(
        max_length=10,
        choices=BALANCE_TYPE_CHOICES,
        default='CHECKING',
        help_text="Balance type this card is linked to"
    )

    def generate_card_number(self):
        prefix = {'visa': '4', 'mastercard': '5', 'amex': '37', 'discover': '6'}.get(self.vendor, '4')
        length = 16 - len(prefix)
        number = prefix + ''.join(random.choices('0123456789', k=length))
        while Card.objects.filter(account=number).exists():
            number = prefix + ''.join(random.choices('0123456789', k=length))
        return number

    def generate_pin(self):
        return ''.join(random.choices('0123456789', k=4))

    def save(self, *args, **kwargs):
        if not self.account:
            self.account = self.generate_card_number()
        if not self.card_password:
            self.card_password = self.generate_pin()
        if not self.expiry_date:
            self.expiry_date = default_expiry_date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.upper()} {self.card_type.capitalize()} Card for {self.user.email} ({self.account[-4:]})"

class LoanRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_requests'
    )
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD'
    )
    loan_type = models.CharField(
        max_length=50,
        default='personal'
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=LOAN_STATUS_CHOICES,
        default='pending'
    )
    term_months = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.00)]
    )
    collateral = models.TextField(
        null=True,
        blank=True
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True
    )
    disbursement_date = models.DateTimeField(
        null=True,
        blank=True
    )
    repayment_start_date = models.DateField(
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans'
    )
    status_detail = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def clean(self):
        if self.status == 'approved':
            if self.approval_date is None:
                raise ValidationError("Approved loans must have an approval date.")
            if self.interest_rate is None:
                raise ValidationError("Approved loans must have an interest rate.")
            if self.term_months is None:
                raise ValidationError("Approved loans must have a term in months.")

    def __str__(self):
        return f"Loan Request by {self.user.email} for {self.amount} {self.currency} on {self.date:%Y-%m-%d}"

class Exchange(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exchanges'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    from_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES
    )
    to_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    date = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        if self.from_currency == self.to_currency:
            raise ValidationError("Source and destination currencies must be different.")

    def __str__(self):
        return f"Exchange of {self.amount} from {self.from_currency} to {self.to_currency} by {self.user.email} - {self.status}"

class ResetPassword(models.Model):
    email = models.EmailField(unique=True)
    reset_code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.reset_code:
            self.reset_code = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"Reset Password for {self.email} (Valid: {self.is_valid()})"

class TransferCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfer_codes'
    )
    tac_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    tax_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    imf_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def generate_unique_code(self, field_name):
        # Generate format: 3 letters + 3 digits (e.g. "ABC123")
        code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(random.choices(string.digits, k=3))

        # Ensure uniqueness
        while TransferCode.objects.filter(**{field_name: code}).exists():
            code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(random.choices(string.digits, k=3))
        return code

    def save(self, *args, **kwargs):
        if not self.tac_code:
            self.tac_code = self.generate_unique_code('tac_code')
        if not self.tax_code:
            self.tax_code = self.generate_unique_code('tax_code')
        if not self.imf_code:
            self.imf_code = self.generate_unique_code('imf_code')
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Transfer Code for {self.user.email} (Valid: {self.is_valid()})"

class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    institution = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    from_account = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        help_text="Card number or account number of source"
    )
    to_account = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        help_text="Card number or account number of destination"
    )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = str(uuid.uuid4())[:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount} by {self.user.email} on {self.transaction_date:%Y-%m-%d}"

class Deposit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deposits'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    TNX = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True
    )
    network = models.CharField(
        max_length=50,
        choices=NETWORK_CHOICES,
        blank=True,
        null=True
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)]
    )
    account = models.CharField(
        max_length=10,
        choices=BALANCE_TYPE_CHOICES,
        default='SAVINGS'
    )
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def save(self, *args, **kwargs):
        if not self.TNX:
            self.TNX = str(uuid.uuid4())[:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deposit of {self.amount} by {self.user.email} on {self.date:%Y-%m-%d}"



class PaymentGateway(models.Model):
    network = models.CharField(
        max_length=50,
        choices=NETWORK_CHOICES,
        unique=True
    )
    deposit_address = models.CharField(
        max_length=255
    )
    qr_code = models.ImageField(
        upload_to='payment_gateways/',
        blank=True,
        null=True
    )
    instructions = models.TextField(
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        # Generate QR code for deposit_address
        if self.deposit_address and not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.deposit_address)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to BytesIO buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Save to ImageField
            file_name = f"qr_{self.network}_{uuid.uuid4().hex[:8]}.png"
            self.qr_code.save(file_name, File(buffer), save=False)
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.network} Gateway"

    class Meta:
        verbose_name = "Payment Gateway"
        verbose_name_plural = "Payment Gateways"



class Beneficiary(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='beneficiaries'
    )
    full_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=255)
    swift_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$', 'Enter a valid SWIFT code.')]
    )
    routing_transit_number = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{9}$', 'Enter a valid 9-digit routing number.')]
    )
    bank_address = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.bank_name}"

class Transfer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD'
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )
    date = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True, null=True)
    region = models.CharField(
        max_length=50,
        default='local'
    )
    charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = str(uuid.uuid4())[:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.reference} of {self.amount} {self.currency} - {self.status}"

class ExchangeRate(models.Model):
    eur_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(0.0001)]
    )
    gbp_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(0.0001)]
    )
    eur_gbp = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(0.0001)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"EUR/USD: {self.eur_usd}, GBP/USD: {self.gbp_usd}, EUR/GBP: {self.eur_gbp}"