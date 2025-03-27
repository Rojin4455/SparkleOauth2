from django.urls import path
from serviceM8.views import *

urlpatterns = [
    path('webhook/', servicem8_webhook, name='servicem8_webhook'),
    path("HandleOAuth/",handle_oauth, name='Oauth'),
    path("subscribe-webhook/", subscribe_webhook),
    path("get-webhooks/", get_webhooks),
    path("remove-webhooks/", remove_webhook),
]