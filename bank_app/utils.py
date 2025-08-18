# utils.py
import random
import string
from .models import Account


def generate_unique_account_id(length=5):
    """
    Generate a unique 5-character account ID for a user.
    Ensures no duplicates exist in the Account model.
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        account_id = ''.join(random.choices(characters, k=length))
        if not Account.objects.filter(account_id=account_id).exists():
            return account_id
