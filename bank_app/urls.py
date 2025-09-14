from django.urls import path,include,re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.views.static import serve 
from django.conf.urls import handler404, handler500


urlpatterns = [
    path('',views.home_page,name='home'),
    path('home/',views.home_page,name='home'),
    path('contact_us/',views.contact_us,name='contact_us'),
    path('Branch_location/',views.Branch_location,name='Branch_location'),
    path('Mortgage_Team/',views.Mortgage_Team,name='Mortgage+Team'),
    path('Our_Legacy/',views.Our_Legacy,name='Our_Legacy'),
    path('Checking/',views.Checking,name='Checking'),
    path('Savings/',views.Savings,name='Savings'),
    path('Catastrophe_Savings/',views.Catastrophe_Savings,name='Catastrophe_Savings'),
    path('cd_ira/',views.cd_ira,name='cd_ira'),
    path('Business_Checking/',views.Business_Checking,name='Business_Checking'),
    path('Rates/',views.Rates,name='Rates'),
    path('Construction/',views.Construction,name='Construction'),
    path('Mortgage_Loans/',views.Mortgage_Loans,name='Mortgage_Loans'),
    path('Mortgage_Team/',views.Mortgage_Team,name='Mortgage_Team'),
    path('Calculators/',views.Calculators,name='Calculators'),
    path('Online_Services/',views.Online_Services,name='Online_Services'),
    path('Card_Services/',views.Card_Services,name='Card_Services'),
    path('Additional_Services/',views.Additional_Services,name='Additional_Services'),
    path('home_buying/',views.home_buying,name='home_buying'),
    path('Refinance_Equity/',views.Refinance_Equity,name='Refinance_Equity'),
    path('We_Care/',views.We_Care,name='We_Care'),
    path('Online_Education/',views.Online_Education,name='Online_Education'),
    path('Credit_Cards/',views.Credit_Cards,name='Credit_Cards'),
    path('Security/',views.Security,name='Security'),
 
#   dashboard pages
    path('register_view/',views.register_view,name='register_view'),
    path('login_view/',views.login_view,name='login_view'),
    path('login/',views.login_view,name='login'),
    path('signup/',views.signup_view,name='signup'),
    path('2FA/',views.pin_page,name='2FA'),
    path('authenticator/',views.authenticator_page,name='authenticator'),
    path('send_2FA_code/',views.send_2FA_code,name='send_2FA_code'),
    path('authen_two_factor/',views.authenticate_two_factor,name='authen_two_factor'),
    path('two_factor_view/',views.two_factor_view,name='two_factor_view'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('transactions/',views.transactions,name='transactions'),
    path('local_transfer/',views.local_transfer,name='local_transfer'),
    path('international_transfer/',views.international_transfer,name='international_transfer'),
    path('loans/',views.loans,name='loans'),
    path('grants/',views.grants,name='grants'),
    path('deposit/',views.deposit,name='deposit'),
    path('currency_swap/',views.currency_swap,name='currency_swap'),
    path('profile/',views.profile,name='profile'),
    path('reset/',views.reset,name='reset'),


    path('local_transfer_be/<int:beneficiary_id>/', views.local_transfer_be, name='local_transfer_be'),
    path('international_transfer_be/<int:beneficiary_id>/', views.international_transfer_be, name='international_transfer_be'),



    # Transactions views 
    path('deposit_view/', views.deposit_view, name='deposit_view'),
    path('get-payment-gateway/', views.get_payment_gateway, name='get_payment_gateway'),
    path('transfer/', views.local_transfer_views, name='transfer'),
    path('validate-pin/', views.validate_pin, name='validate_pin'),
    path('send-transfer-code/', views.send_transfer_code, name='send_transfer_code'),
    path('validate-code/', views.validate_code, name='validate_code'),
    path("receipt/<str:reference>/", views.transaction_receipt_view, name="transaction_receipt"),
    path('internal_transfer/', views.internal_transfer_views, name='internal_transfer'),
    path('exchange_submit/', views.exchange_submit_view, name='exchange_submit'),
    path('loan/request/', views.loan_request_view, name='loan_request_view'),
    path('logout/',views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path("update_password/", views.update_password, name="update_password"),
    path("update_pin/", views.update_pin, name="update_pin"),
    path("toggle_2fa/", views.toggle_2fa, name="toggle_2fa"),
    path('add-beneficiary/', views.add_beneficiary, name='add_beneficiary'),



    re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
]


# handler404 = views.custom_404_view
# handler500 = views.custom_500_view
 
 

