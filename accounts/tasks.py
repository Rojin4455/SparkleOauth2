# your_app_name/tasks.py
import requests
from celery import shared_task
from accounts.models import GHLAuthCredentials
from django.conf import settings
from datetime import datetime
from serviceM8.models import ServiceM8Token
from decouple import config
from serviceM8.utils import fetch_servicem8_job, fetch_servicem8_client,fetch_job_category, get_or_create_client, get_or_create_job, fetch_job_contact, fetch_company_contact


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


@shared_task
def make_api_for_ghl():
    
    credentials = GHLAuthCredentials.objects.first()
    
    print("credentials tokenL", credentials)
    refresh_token = credentials.refresh_token

    
    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data={
        'grant_type': 'refresh_token',
        'client_id': settings.GHL_CLIENT_ID,
        'client_secret': settings.GHL_CLIENT_SECRET,
        'refresh_token': refresh_token
    })
    
    new_tokens = response.json()
    print("newtoken :", new_tokens)

    obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= new_tokens.get("locationId"),
            defaults={
                "access_token": new_tokens.get("access_token"),
                "refresh_token": new_tokens.get("refresh_token"),
                "expires_in": new_tokens.get("expires_in"),
                "scope": new_tokens.get("scope"),
                "user_type": new_tokens.get("userType"),
                "company_id": new_tokens.get("companyId"),
                "user_id":new_tokens.get("userId"),

            }
        )




@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def handle_webhook_event(self,data):
    # print("Reached here event")
    # print("Webhook data:", data)
    uuid = None
    print("data:-------- ", data)

    

    
    # Extract UUID from different possible webhook data structures
    if "entry" in data and isinstance(data["entry"], list) and len(data["entry"]) > 0:
        uuid = data["entry"][0].get("uuid")
            
    if not uuid and "eventArgs" in data and "entry" in data["eventArgs"]:
        entry_list = data["eventArgs"]["entry"]
        if isinstance(entry_list, list) and len(entry_list) > 0:
            uuid = entry_list[0].get("uuid")
            
    if not uuid:
        print("No valid UUID found in webhook data")
        return {"status": "error", "message": "No valid UUID found"}
        
    try:
        serviceM8token = ServiceM8Token.objects.first()
        if not serviceM8token or not serviceM8token.access_token:
            print("No valid ServiceM8 token found")
            return {"status": "error", "message": "No valid ServiceM8 token"}
    except Exception as e:
        print(f"Error retrieving ServiceM8 token: {str(e)}")
        return {"status": "error", "message": f"Token error: {str(e)}"}
    
        
    
    
    
    # Get company UUID and fetch client data
    # Fetch job data
    job_data = fetch_servicem8_job(uuid, serviceM8token.access_token)
    if not job_data:
        print("Failed to fetch job data from ServiceM8")
        return {"status": "error", "message": "Failed to fetch job data"}

    company_uuid = job_data.get('company_uuid')
    if not company_uuid:
        print("No company UUID found in job data")
        return {"status": "error", "message": "No company UUID in job data"}

            

    client_data = fetch_servicem8_client(company_uuid, serviceM8token.access_token)
    print("client:data", client_data)
    if not client_data:
        print("Failed to fetch client data from ServiceM8")
        return {"status": "error", "message": "Failed to fetch client data"}
    
    # Fetch contact information
    job_contact_data = fetch_job_contact(job_data.get("uuid"), serviceM8token.access_token)
    if not job_contact_data:
        # Try to fetch from company contacts as fallback
        job_contact_data = fetch_company_contact(client_data.get('uuid'), serviceM8token.access_token)
    
    # Get GHL token
    try:
        ghl_credentials = GHLAuthCredentials.objects.first()
        if not ghl_credentials or not ghl_credentials.access_token:
            print("No valid GHL credentials found")
            return {"status": "error", "message": "No valid GHL credentials"}
        ghl_token = ghl_credentials.access_token
    except Exception as e:
        print(f"Error retrieving GHL credentials: {str(e)}")
        return {"status": "error", "message": f"GHL credential error: {str(e)}"}
    
    # Extract contact info or use empty dict if no contacts found
    contact_info = job_contact_data[-1] if job_contact_data and isinstance(job_contact_data, list) and len(job_contact_data) > 0 else {}

    if job_data.get("category_uuid"):
        job_category_data = fetch_job_category(job_data.get("category_uuid"), serviceM8token.access_token)
        if job_category_data:
            job_data["category_name"] = job_category_data.get("name")
            client_data['category_name'] = job_category_data.get("name")
    client_data['job_is_scheduled_until_stamp'] = job_data.get("job_is_scheduled_until_stamp")

    
    print("job_data:  -----", job_data)

    comparison_date = datetime.strptime("2025-03-10", "%Y-%m-%d")
    job_date = datetime.strptime(job_data.get("date", "0000-00-00 00:00:00"), "%Y-%m-%d %H:%M:%S")

    try:

        if job_date > comparison_date and job_data.get("category_name","") != "Repeated Customer" and "Re engage" not in job_data.get("job_description",""):
            print("Job date is after 2025-03-10")
            client = get_or_create_client(client_data, contact_info, ghl_token)
            job = get_or_create_job(job_data, client, ghl_token)
            return {"status": "success", "job_id": job.uuid, "client_id": client.uuid}
        else:
            print("Job date is on or before 2025-03-18")
            return {"status": "error", "message": "Job date is on or before 2025-03-18"}
    except Exception as e:
        print(f"Error processing client/job data: {str(e)}")
        return {"status": "error", "message": f"Processing error: {str(e)}"}



