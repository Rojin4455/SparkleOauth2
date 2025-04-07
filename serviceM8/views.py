
from django.http import HttpResponse
from urllib.parse import urlparse
import base64
from decouple import config
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
from accounts.tasks import handle_webhook_event
from serviceM8.models import ServiceM8Log, ServiceM8Token, ServiceM8WebhookLog
import requests


def handle_oauth(request):
    # Step 1: Get the 'code' from the request
    code = request.GET.get("code")
    
    if not code:
        return JsonResponse({"error": "Authorization code missing"}, status=400)

    # Step 2: Exchange 'code' for an access token
    token_url = "https://go.servicem8.com/oauth/access_token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": config("SERVICEM8_APP_ID"),
        "client_secret": config("SERVICEM8_APP_SECRET"),
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


@csrf_exempt
def servicem8_webhook(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Log request headers
    headers = dict(request.headers)
    ServiceM8WebhookLog.objects.create(
        logger="Webhook POST method triggered", 
        entry_data={"headers": headers, "content_type": request.content_type}
    )

    # 1. Webhook verification challenge
    if request.POST.get('mode') == 'subscribe' and 'challenge' in request.POST:
        challenge = request.POST.get('challenge')
        ServiceM8WebhookLog.objects.create(
            logger="Webhook verification challenge received", 
            entry_data={"challenge": challenge}
        )
        return HttpResponse(challenge, content_type='text/plain')

    # 2. Handle JSON Webhooks
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
            ServiceM8WebhookLog.objects.create(
                logger="Webhook received JSON data", 
                entry_data=data
            )
            # Fix: Pass data as a tuple by adding a comma
            # threading.Thread(target=handle_webhook_event, args=(data,)).start()
            handle_webhook_event.delay(data)
            return HttpResponse("Webhook received", status=200)
        except json.JSONDecodeError as e:
            ServiceM8WebhookLog.objects.create(
                logger="Webhook error - Invalid JSON", 
                entry_data={"error": str(e), "body": request.body.decode("utf-8")}
            )
            return HttpResponse("Invalid JSON", status=400)

    # 3. Handle Form-Encoded Webhooks (Base64 / JWT-like format)
    elif request.content_type == "application/x-www-form-urlencoded":
        try:
            # Log raw form data for debugging
            ServiceM8WebhookLog.objects.create(
                logger="Form-encoded webhook received",
                entry_data={"raw_post_data": dict(request.POST)}
            )
            
            # Get the first key from request.POST
            if not request.POST:
                return HttpResponse("Empty form data", status=200)
                
            encoded_payload_key = list(request.POST.keys())[0]
            
            # Decode the base64/JWT-like string
            parts = encoded_payload_key.split(".")  # JWT format uses dots (.)
            
            if len(parts) >= 2:  # It's likely a JWT-like structure
                # Handle potential padding issues
                padding_needed = len(parts[1]) % 4
                if padding_needed:
                    parts[1] += "=" * (4 - padding_needed)
                
                try:
                    decoded_bytes = base64.urlsafe_b64decode(parts[1])
                    decoded_str = decoded_bytes.decode("utf-8")
                    data = json.loads(decoded_str)
                    
                    ServiceM8WebhookLog.objects.create(
                        logger="Webhook decoded job data", 
                        entry_data=data
                    )
                    # Fix: Pass data as a tuple by adding a comma
                    # threading.Thread(target=handle_webhook_event, args=(data,)).start()
                    handle_webhook_event.delay(data)

                    return HttpResponse("Webhook processed", status=200)
                except Exception as e:
                    ServiceM8WebhookLog.objects.create(
                        logger="Webhook error - JWT payload decoding failed", 
                        entry_data={"error": str(e), "jwt_part": parts[1]}
                    )
                    return HttpResponse("JWT payload decoding error", status=200)
            else:
                # Try to process as a plain webhook
                try:
                    data = json.loads(encoded_payload_key)
                    ServiceM8WebhookLog.objects.create(
                        logger="Webhook processed as plain JSON", 
                        entry_data=data
                    )
                    # threading.Thread(target=handle_webhook_event, args=(data,)).start()
                    handle_webhook_event.delay(data)

                    return HttpResponse("Webhook processed", status=200)
                except json.JSONDecodeError:
                    ServiceM8WebhookLog.objects.create(
                        logger="Webhook error - Unrecognized format", 
                        entry_data={"raw_data": encoded_payload_key[:1000]}  # Truncate if too large
                    )
                    return HttpResponse("Invalid webhook format", status=200)
        except Exception as e:
            ServiceM8WebhookLog.objects.create(
                logger="Webhook error - Processing failed", 
                entry_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            return HttpResponse("Processing error", status=200)

    # 4. Handle any other content types
    else:
        ServiceM8WebhookLog.objects.create(
            logger="Webhook error - Unsupported content type", 
            entry_data={"content_type": request.content_type}
        )
        return HttpResponse(f"Unsupported Content-Type: {request.content_type}", status=200)





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
        "fields": "uuid,status,job_address,billing_address,job_description,work_done_description,payment_amount,quote_date,quote_sent,work_order_date,job_is_scheduled_until_stamp,quote_sent_stamp,category_uuid,total_invoice_amount"
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
    body_data = json.loads(request.body)
    ServiceM8WebhookLog.objects.create(logger="subscribe webhook function data",entry_data = body_data)


    callback_url = body_data.get("callback_url")
    fields = body_data.get("fields")
    print(f"token: {token} callback_url : {callback_url}  fields: {fields}")

    create_servicem8_webhook(token.access_token, callback_url=callback_url)
    return JsonResponse({"message":"success"})



def remove_webhook(request):
    url = "https://api.servicem8.com/webhook_subscriptions"
    token = ServiceM8Token.objects.first()

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"

    }

    response = requests.delete(url, headers=headers)

    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()

        return JsonResponse(response.json(), safe=False)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "Failed to remove webhook", "details": str(e)}, status=500)




def get_webhooks(request):

    url = "https://api.servicem8.com/webhook_subscriptions"
    token = ServiceM8Token.objects.first()


    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "accept": "application/json"
        }

    response = requests.get(url, headers=headers)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return JsonResponse(response.json(), safe=False)

    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "Failed to fetch webhooks", "details": str(e)}, status=500)

def url_webhook():
    url = "https://api.servicem8.com/api_1.0/Job/49dcdf87-3801-4f74-b328-228fcffd887d.json"
    token = ServiceM8Token.objects.first()

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"

    }

    response = requests.get(url, headers=headers)

    print(response.text)


