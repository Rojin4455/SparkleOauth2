
from django.http import HttpResponse

from accounts.models import GHLAuthCredentials

from urllib.parse import urlparse

from decouple import config
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import threading
import traceback
from serviceM8.models import ServiceM8Log, ServiceM8Token, ServiceM8WebhookLog
from serviceM8.utils import fetch_servicem8_job, fetch_servicem8_client, fetch_company_contact, fetch_job_contact, get_or_create_client, get_or_create_job

@csrf_exempt
def servicem8_webhook2(request):
    if request.method == 'POST':
        try:
            webhook_data = json.loads(request.body)
            event_type = webhook_data.get('eventType')

            # Log the webhook received event
            log_entry = ServiceM8Log(status="started", event_type=event_type)
            log_entry.set_servicem8_data(webhook_data)
            log_entry.save()

            # Respond immediately so ServiceM8 does not wait
            threading.Thread(target=process_webhook_data, args=(webhook_data, log_entry)).start()
            return JsonResponse({'status': 'success', 'message': 'Webhook received, processing in background'}, status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def process_webhook_data(webhook_data, log_entry):
    """Handles webhook processing asynchronously."""
    try:
        event_type = webhook_data.get('eventType')
        entry_data = webhook_data.get('eventData', {})
        if event_type == 'Webhook_Subscription' and entry_data.get('object') == 'Job':
            entries = entry_data.get('entry', [])
            if not entries:
                log_entry.status = "warning"
                log_entry.error_message = "No entries found in webhook data"
                log_entry.save()
                return
            
            job_uuid = entries[0].get('uuid')
            log_entry.job_uuid = job_uuid
            log_entry.save()

            auth_data = webhook_data.get('rawEvent', {}).get('auth', {})
            access_token = auth_data.get('accessToken')

            if not access_token:
                log_entry.status = "error"
                log_entry.error_message = "Access token missing from ServiceM8"
                log_entry.save()
                return
            
            # Fetch job and client data
            job_data = fetch_servicem8_job(job_uuid, access_token)
            if not job_data:
                log_entry.status = "error"
                log_entry.error_message = "Failed to fetch job data"
                log_entry.save()
                return
            
            company_uuid = job_data.get('company_uuid')
            if not company_uuid:
                log_entry.status = "error"
                log_entry.error_message = "Client details missing to create job"
                log_entry.save()
                return

            log_entry.client_uuid = company_uuid
            log_entry.save()

            client_data = fetch_servicem8_client(company_uuid, access_token)
            if not client_data:
                log_entry.status = "error"
                log_entry.error_message = "Failed to fetch client data"
                log_entry.save()
                return
            
            job_contact = fetch_job_contact(job_data.get("uuid"), access_token) or fetch_company_contact(client_data.get('uuid'), access_token)

            ghl_credentials = GHLAuthCredentials.objects.first()
            if not ghl_credentials:
                log_entry.status = "error"
                log_entry.error_message = "GHL authentication credentials not found"
                log_entry.save()
                return

            ghl_token = ghl_credentials.access_token

            # Process client and job creation
            client = get_or_create_client(client_data, job_contact[-1] if job_contact else {}, ghl_token)
            job = get_or_create_job(job_data, client, ghl_token)

            log_entry.client_link_successful = True
            log_entry.job_link_successful = True
            log_entry.ghl_client_id = client.ghl_id
            log_entry.ghl_job_id = job.ghl_id
            log_entry.status = "success"
            log_entry.save()

    except Exception as e:
        log_entry.status = "error"
        log_entry.error_message = str(e)
        log_entry.stack_trace = traceback.format_exc()
        log_entry.save()



import requests


CLIENT_ID = "853518"
CLIENT_SECRET = "f4eacb6da26d45eba89a2286f8865b4b"

def handle_oauth(request):
    # Step 1: Get the 'code' from the request
    code = request.GET.get("code")
    
    if not code:
        return JsonResponse({"error": "Authorization code missing"}, status=400)

    # Step 2: Exchange 'code' for an access token
    token_url = "https://go.servicem8.com/oauth/access_token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": config("SERVICEM8_REDIRECT_URI")
    }

    print("payload:", payload)

    response = requests.post(token_url, data=payload)

    print("response: ", response.status_code)

    # Step 3: Handle the response
    if response.status_code == 200:
        token_data = response.json()
        ServiceM8Token.update_token(token_data)
        return JsonResponse(token_data)  # Return the access token
    else:
        return JsonResponse({"error": "Failed to get access token", "details": response.text}, status=400)





from django.http import HttpResponse, JsonResponse
import json

def servicem8_webhook(request):
    if request.method == "POST":
        ServiceM8WebhookLog.objects.create(logger="Webhook POST method triggered")
        
        try:
            data = json.loads(request.body)
            ServiceM8WebhookLog.objects.create(logger="Webhook received data", entry_data=data)

            # Webhook verification
            if data.get("mode") == "subscribe" and "challenge" in data:
                ServiceM8WebhookLog.objects.create(logger="Webhook verification challenge", entry_data={"challenge": data["challenge"]})
                return HttpResponse(data["challenge"])  # Respond with the challenge

            # Handle webhook events
            handle_webhook_event(data)

            return JsonResponse({"status": "received"}, status=200)

        except json.JSONDecodeError:
            ServiceM8WebhookLog.objects.create(logger="Webhook error - Invalid JSON")
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        except Exception as e:
            ServiceM8WebhookLog.objects.create(logger="Webhook error", entry_data={"error": str(e)})
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "GET":
        ServiceM8WebhookLog.objects.create(logger="Webhook GET method triggered")
        challenge = request.GET.get('challenge')
        if challenge:
            ServiceM8WebhookLog.objects.create(logger="Webhook GET challenge received", entry_data={"challenge": challenge})
            return HttpResponse(challenge)

    return JsonResponse({"error": "Invalid request method"}, status=405)
def handle_webhook_event(data):
    print("reached here event")
    """Process the webhook event"""
    object_type = data.get("object")
    entries = data.get("entry", [])

    for entry in entries:
        print(f"Webhook Received: {object_type} Updated - {entry}")



def create_servicem8_webhook(access_token, callback_url, fields=None):

    url = "https://api.servicem8.com/webhook_subscriptions"


    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
    }

    payload = {
        "object": "job",
        "callback_url": callback_url,
        "fields": "status"
    }
    ServiceM8WebhookLog.objects.create(logger  = "create_servicem8_webhook triggered", entry_data=payload)


    response = requests.post(url, data=payload, headers=headers)
    print("responseL : ", response.text)
    try:
        response.json()
        ServiceM8WebhookLog.objects.create(logger  = "create_servicem8_webhook after request to serviceM8", entry_data=response.json() )

    except requests.exceptions.JSONDecodeError:
        print("Failed to decode JSON, response text:", response.text)
        ServiceM8WebhookLog.objects.create(logger  = response.text)

        return {"error": "Invalid JSON response", "status_code": response.status_code, "response_text": response.text}


def subscribe_webhook(request):
    token = ServiceM8Token.objects.first()
    ServiceM8WebhookLog.objects.create(logger="initial webhook subscribe triggered")
    body_data = json.loads(request.body)  # Parse raw request body
    ServiceM8WebhookLog.objects.create(logger="subscribe webhook function data",entry_data = body_data)


    callback_url = body_data.get("callback_url")
    fields = body_data.get("fields")
    print(f"token: {token} callback_url : {callback_url}  fields: {fields}")

    create_servicem8_webhook(token.access_token, callback_url=callback_url, fields=fields)
    return JsonResponse({"message":"success"})

