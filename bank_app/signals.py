from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Account, AccountBalance, CurrencyBalance, Card
from .models import BALANCE_TYPE_CHOICES  # make sure these are defined in models.py

@receiver(post_save, sender=Account)
def create_related_objects_for_account(sender, instance, created, **kwargs):
    if created:
        # Create AccountBalance if not exists
        account_balance, _ = AccountBalance.objects.get_or_create(account=instance)

        # Create CurrencyBalance for GBP and EUR
        for currency in ['GBP', 'EUR']:
            for balance_type in BALANCE_TYPE_CHOICES:
                CurrencyBalance.objects.get_or_create(
                    account_balance=account_balance,
                    currency=currency,
                    balance_type=balance_type[0],
                    defaults={'balance': 0.00}
                )

        # Create Visa debit card for non-admin users
        if not (instance.is_staff or instance.is_superuser):
            Card.objects.get_or_create(
                user=instance,
                card_type='debit',
                vendor='visa',
                status='pending',
                balance_type='CHECKING'
            )
