from django.apps import AppConfig

class BankAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bank_app'

    def ready(self):
        import bank_app.signals
