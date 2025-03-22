from django.urls import path
from serviceM8.views import *

urlpatterns = [
    path('webhook/', servicem8_webhook, name='servicem8_webhook'),
    path("HandleOAuth/",handle_oauth, name='Oauth'),
    path("subscribe-webhook/", subscribe_webhook)
]