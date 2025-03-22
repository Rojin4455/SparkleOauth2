# your_app_name/tasks.py
import requests
from celery import shared_task
from accounts.models import GHLAuthCredentials
from django.conf import settings
from datetime import datetime
from serviceM8.models import ServiceM8Token
from decouple import config

@shared_task
def make_api_call():


    def handle_refresh():
        token = ServiceM8Token.objects.first()
        token_url = "https://go.servicem8.com/oauth/access_token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": config("SERVICEM8_APP_ID"),
            "client_secret": config("SERVICEM8_APP_SECRET"),
            "refresh_token": token.refresh_token
        }

        print("payload:", payload)

        response = requests.post(token_url, data=payload)

        print("response: ", response.status_code)

        if response.status_code == 200:
            token_data = response.json()
            ServiceM8Token.update_token(token_data)
            
        else:
            print("Failed to refresh token:", response.text)
    handle_refresh()
    
    # credentials = GHLAuthCredentials.objects.first()
    
    # print("credentials tokenL", credentials)
    # refresh_token = credentials.refresh_token

    
    # response = requests.post('https://services.leadconnectorhq.com/oauth/token', data={
    #     'grant_type': 'refresh_token',
    #     'client_id': settings.GHL_CLIENT_ID,
    #     'client_secret': settings.GHL_CLIENT_SECRET,
    #     'refresh_token': refresh_token
    # })
    
    # new_tokens = response.json()
    # print("newtoken :", new_tokens)

    # obj, created = GHLAuthCredentials.objects.update_or_create(
    #         location_id= new_tokens.get("locationId"),
    #         defaults={
    #             "access_token": new_tokens.get("access_token"),
    #             "refresh_token": new_tokens.get("refresh_token"),
    #             "expires_in": new_tokens.get("expires_in"),
    #             "scope": new_tokens.get("scope"),
    #             "user_type": new_tokens.get("userType"),
    #             "company_id": new_tokens.get("companyId"),
    #             "user_id":new_tokens.get("userId"),

    #         }
    #     )



