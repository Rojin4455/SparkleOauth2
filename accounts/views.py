
from django.shortcuts import render,redirect
from decouple import config
from django.http import JsonResponse
import requests
from accounts.models import GHLAuthCredentials
from datetime import datetime


# Create your views here.
GHL_CLIENT_ID = config("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = config("GHL_CLIENT_SECRET")
GHL_REDIRECTED_URI = config("GHL_REDIRECTED_URI")
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"


SCOPE = "contacts.readonly%20contacts.write%20opportunities.readonly%20opportunities.write%20locations/customValues.readonly%20locations/customValues.write"
LOCATION_ID = "zPbyOYoNWW8AzKRkMekd"


def auth_connect(request):
    auth_url = ("https://marketplace.leadconnectorhq.com/oauth/chooselocation?response_type=code&"
                f"redirect_uri={GHL_REDIRECTED_URI}&"
                f"client_id={GHL_CLIENT_ID}&"
                f"scope={SCOPE}"
                )
    return redirect(auth_url)

def callback(request):
    
    code = request.GET.get('code')

    if not code:
        return JsonResponse({"error": "Authorization code not received from OAuth"}, status=400)

    return redirect(f'http://localhost:8000/accounts/auth/tokens?code={code}')



def tokens(request):
    authorization_code = request.GET.get("code")

    if not authorization_code:
        return JsonResponse({"error": "Authorization code not found"}, status=400)

    data = {
        "grant_type": "authorization_code",
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "redirect_uri": 'http://localhost:8000/accounts/oauth/callback/',
        "code": authorization_code,
    }

    response = requests.post(TOKEN_URL, data=data)

    try:
        response_data = response.json()
        if not response_data:
            return

        obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= response_data.get("locationId"),
            defaults={
                "access_token": response_data.get("access_token"),
                "refresh_token": response_data.get("refresh_token"),
                "expires_in": response_data.get("expires_in"),
                "scope": response_data.get("scope"),
                "user_type": response_data.get("userType"),
                "company_id": response_data.get("companyId"),
                "user_id":response_data.get("userId"),

            }
        )
        
        
        
        return JsonResponse({
            "message": "Authentication successful",
            "access_token": response_data.get('access_token'),
            "token_stored": True
        })
        
    except requests.exceptions.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid JSON response from API",
            "status_code": response.status_code,
            "response_text": response.text[:500]
        }, status=500)



def create_contact():
    token = GHLAuthCredentials.objects.first()
    ACCESS_TOKEN = token.access_token
    
    url = "https://services.leadconnectorhq.com/contacts/"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }
    
    # First, get the custom field ID for your ServiceM8UUID field
    # custom_fields_url = f"https://services.leadconnectorhq.com/locations/{LOCATION_ID}/customFields"
    # custom_fields_response = requests.get(custom_fields_url, headers=headers)
    # custom_fields = custom_fields_response.json().get('customFields', [])
    
    # service_m8_field_id = None
    # for field in custom_fields:
    #     if field.get('name') == 'ServiceM8UUID':
    #         service_m8_field_id = field.get('id')
    #         break
    
    # if not service_m8_field_id:
    #     return JsonResponse({"error": "Custom field 'ServiceM8UUID' not found"}, status=404)
    
    # Now create the contact with the custom field
    data = {
        "firstName": "test3 local",
        "email": "testcontw33@example.com",
        "locationId": LOCATION_ID,
        "customFields": [
            {
            "id": "r2Z4vtJv3VPmE30tlxcg",
            "key": "Service M8 Client Id",
            "field_value": "903916078812"
            }
        ]
    }
    
    response = requests.post(url, json=data, headers=headers)
    print("response:", response.json())
    
    return JsonResponse(response.json())

# print("create contact: ", create_contact())






