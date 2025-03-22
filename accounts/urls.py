from django.urls import path
from .views import *

urlpatterns = [
    path("auth/connect/", auth_connect, name="oauth_connect"),
    path("auth/callback/", callback, name="oauth_callback"),
    path("auth/tokens/", tokens, name="oauth_tokens"),
    path('create-contact/', create_contact, name="create_contact"),

]