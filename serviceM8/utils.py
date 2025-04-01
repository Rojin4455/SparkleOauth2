import requests
import urllib.parse
from serviceM8.models import Job, Client, ServiceM8Token
from decouple import config

LOCATION_ID = "zPbyOYoNWW8AzKRkMekd"



def map_servicem8_status_to_ghl(status):
    status_mapping = {
        "Quote": "open",
        "Work Order": "won",
        "Completed": "won",
        "Unsuccessful": "lost"
    }

    return status_mapping.get(status, "open")


def map_servicem8_status_to_ghl_pipeline(status):
    status_mapping = {
        "Quote": "51ccc299-cdac-48bf-a7c8-aaf77fa4a797",
        "Work Order": "ee748731-1c88-4098-9a1c-a849739adf30",  # quot sent id "5b2386b8-7bcd-41b2-879b-f1d9d04ea464",
        "Completed": "ee748731-1c88-4098-9a1c-a849739adf30",
        "Unsuccessful": "84239738-ec63-4d67-bc1c-2d454e770688"
    }

    return status_mapping.get(status, "51ccc299-cdac-48bf-a7c8-aaf77fa4a797")

def get_pipeline_stage_id_for_quote(quote_sent, quote_sent_stamp, job_is_scheduled_until_stamp):
    new_lead_id = "51ccc299-cdac-48bf-a7c8-aaf77fa4a797"  # New Lead
    quote_booked_id = "d417fa3f-52df-426d-895b-4b9cfb0cfabf"  # Quote Booked
    quote_sent_id = "5b2386b8-7bcd-41b2-879b-f1d9d04ea464"  # Quote Sent

    if job_is_scheduled_until_stamp == "0000-00-00 00:00:00":
        if quote_sent and quote_sent_stamp != "0000-00-00 00:00:00":
            return quote_sent_id  # Quote Sent
        return new_lead_id  # New Lead

    if job_is_scheduled_until_stamp != "0000-00-00 00:00:00":
        if quote_sent and quote_sent_stamp != "0000-00-00 00:00:00":
            return quote_sent_id  # Quote Sent
        return quote_booked_id  # Quote Booked

    return None


def fetch_servicem8_job(job_uuid, access_token):
    """Fetch job details from ServiceM8 API"""
    try:
        url = f"https://api.servicem8.com/api_1.0/job/{job_uuid}.json"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching job from ServiceM8: {str(e)}")
        return None
    



def fetch_servicem8_client(company_uuid, access_token):
    """Fetch client details from ServiceM8 API"""
    try:
        url = f"https://api.servicem8.com/api_1.0/Company/{company_uuid}.json"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching client from ServiceM8: {str(e)}")
        return None
    

def fetch_job_category(category_uuid, access_token):
    try:
        url = f"https://api.servicem8.com/api_1.0/category/{category_uuid}.json"

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {access_token}"
        }

        response = requests.get(url, headers=headers) 
        response.raise_for_status()
  
        return response.json()
    except Exception as e:
        print(f"Error fetching job category from ServiceM8: {str(e)}")
        return None 

def fetch_company_contact(company_id, token):
    try:
        filter_param = urllib.parse.quote(f"company_uuid eq '{company_id}'")
        url = f"https://api.servicem8.com/api_1.0/companycontact.json?$filter={filter_param}"
        headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("success", response)
        return response.json()
    except Exception as e:
        print(f"Error fetching client from ServiceM8: {str(e)}")
        return None


def fetch_job_contact(job_id, token):
    try:
        filter_param = urllib.parse.quote(f"job_uuid eq '{job_id}'")
        url = f"https://api.servicem8.com/api_1.0/jobcontact.json?$filter={filter_param}"
        headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error fetching client from ServiceM8: {str(e)}")
        return None


def get_or_create_client(client_data,job_contact, ghl_token):
    client_name = ""
    if job_contact.get("first"):
        client_name = job_contact.get("first") + " " + job_contact.get("last","")
    client, created = Client.objects.get_or_create(
        uuid=client_data.get("uuid"),
        defaults={
            "name": client_name if client_name else  client_data.get("name",""),
            "email": job_contact.get("email", ""),
            "address": client_data.get("address"),
            "mobile":job_contact.get("mobile", "phone"),
        }
    )

    if not created:
        client.name = client_name if client_name else  client_data.get("name","")
        client.email = job_contact.get("email", "") if job_contact.get("email", "") else client.email
        client.address = client_data.get("address") if client_data.get("address") else client.address
        client.mobile = job_contact.get("mobile", "phone") if job_contact.get("mobile", "phone") else client.mobile
        client.save()
    
    if client.ghl_id:
        print("enter here update1")
        update_ghl_contact(client, client_data, ghl_token, job_contact)
        return client
    
    contact_result = create_ghl_contact(client, client_data, ghl_token, job_contact)
    print("results of contact create:",contact_result)
    if contact_result and contact_result.get("id"):
        client.ghl_id = contact_result.get("id")
        client.save()
    return client

def get_or_create_job(job_data,client_obj, ghl_token):
    job, created = Job.objects.get_or_create(
        uuid=job_data.get("uuid"),
        defaults={
            "job_address": job_data.get("job_address"),
            "status": job_data.get("status"),
            "client": client_obj,
            "ghl_id": None
        }
    )
    if not created:
        job.status = job_data.get("status")
        job.job_address = job_data.get("job_address")
        job.save()
    
    if job.ghl_id:
        print("update opper triggered: -----------------------------------")
        update_ghl_opportunity(job.ghl_id, job_data, client_obj ,ghl_token)
        return job

    opportunity_result = create_ghl_opportunity(job_data,client_obj, ghl_token)
    if opportunity_result and opportunity_result.get("id"):
        job.ghl_id = opportunity_result.get("id")
        job.save()
    return job




def create_ghl_opportunity(job_data, client_obj, ghl_token):
    ghl_api_url = "https://services.leadconnectorhq.com/opportunities/"
    headers = {
        "Authorization": f"Bearer {ghl_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"

    }
    pipline_stage_id = False
    if job_data.get("status") == "Quote":
        pipline_stage_id = get_pipeline_stage_id_for_quote(job_data.get("quote_sent"), job_data.get("quote_sent_stamp"), job_data.get("job_is_scheduled_until_stamp"))

    
    payload = {
        "pipelineId":"kSt63A9h2lw1LL1cp7Hx",
        "name": f"{client_obj.name} - #{job_data.get("generated_job_id", "New Job")}",
        "locationId":LOCATION_ID,
        "status": map_servicem8_status_to_ghl(job_data.get("status", "open")),
        "pipelineStageId":pipline_stage_id if pipline_stage_id else map_servicem8_status_to_ghl_pipeline(job_data.get("status","d417fa3f-52df-426d-895b-4b9cfb0cfabf")),
        "contactId": client_obj.ghl_id,
        "monetaryValue": job_data.get("total_invoice_amount", 0),
        "source":job_data.get("category_name", "serviceM8"),
        "customFields": [
                {
                    "id": "b7zOencMXS3P6rgtiJqU", #street address
                    "field_value": job_data.get("job_address","")
                },
                {
                    "id": "2MZf3im3WK6dh5zklDi7", # Job description
                    "field_value": job_data.get("job_description","")
                }
        ],
    }
    response = requests.post(ghl_api_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json().get("opportunity",[])
    return None

import re

def format_phone_number(number):
    if not number:
        return None

    # Remove spaces and non-numeric characters (except +)
    number = re.sub(r"[^\d+]", "", number)

    # If number starts with "+61", strip it and keep only the next 9 digits
    if number.startswith("+61"):
        number = number[3:]  # Remove "+61"
    
    # Extract only the last 9 digits
    number = number[-9:]

    # Prefix with "+61"
    return f"%2B61{number}"

def create_ghl_contact(client, client_data, ghl_token, job_contact):
    """Create or update a contact in GoHighLevel from ServiceM8 client data"""
    from datetime import datetime
    try:
        # Normalize phone numbers
        mobile = format_phone_number(job_contact.get("mobile",""))
        phone = format_phone_number(job_contact.get("phone",""))
        
        # Initialize contact as None
        contact = None

        print("client data: --------------------------------------", client_data)
        print("job contact data: --------------------------------------", job_contact)
        
        # Try to find existing contact by mobile or phone
        if mobile:
            contact = get_ghl_contacts(LOCATION_ID, mobile, ghl_token)
        if contact and not contact.get('contacts') and phone:
            contact = get_ghl_contacts(LOCATION_ID, phone, ghl_token)
        
        # Prepare name parts
        name_parts = client.name.split(" ", 1)
        full_name = client.name
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""


        
        # Prepare base payload
        base_payload = {
            "name": full_name,
            "firstName": first_name,
            "lastName": last_name,
            "address1": client_data.get('address_street', ''),
            "tags": ["ServiceM8"]
        }

        if client_data.get("job_is_scheduled_until_stamp") != "0000-00-00 00:00:00":
            job_date = datetime.strptime(client_data["job_is_scheduled_until_stamp"], "%Y-%m-%d %H:%M:%S")
            formatted_date = job_date.strftime("%d-%b-%Y %I:%M %p").upper()

            
            base_payload["customFields"] =  [{
                "id": "3Fd9Deng6jrRwuCPSfd0",
                "field_value": formatted_date
            }]
        
        if client_data.get("category_name"):
            base_payload["source"] = client_data.get("category_name")
        
        # Determine if this is an update or new contact creation
        if contact and contact.get('contacts'):
            # Contact exists - prepare for update
            contact_id = contact['contacts'][0].get('id')
            url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
            
            # Add email and phone only if not already present
            existing_contact = contact['contacts'][0]
            if not existing_contact.get('email'):
                base_payload['email'] = client.email

            print("base payload: ,", base_payload)
            
            # Use PUT for update
            response = requests.put(url, 
                headers={
                    'Authorization': f'Bearer {ghl_token}',
                    'Content-Type': 'application/json',
                    "Version": "2021-07-28",
                }, 
                json=base_payload
            )
        else:
            # New contact creation
            url = "https://services.leadconnectorhq.com/contacts/"
            base_payload.update({
                "phone": client.mobile,
                "email": client.email,
                "locationId": LOCATION_ID

            })
            
            # Use POST for new contact
            response = requests.post(url, 
                headers={
                    'Authorization': f'Bearer {ghl_token}',
                    'Content-Type': 'application/json',
                    "Version": "2021-07-28",
                }, 
                json=base_payload
            )
        
        # Check response
        response.raise_for_status()
        return response.json().get('contact')
    
    except requests.exceptions.RequestException as e:
        print(f"Error creating/updating contact: {e}")
        return None


def update_ghl_contact(client,client_data, ghl_token, job_contact):
    from datetime import datetime

    """Update existing contact in GoHighLevel with ServiceM8 client data"""
    try:
        url = f"https://services.leadconnectorhq.com/contacts/{client.ghl_id}"
        headers = {
            'Authorization': f'Bearer {ghl_token}',
            'Content-Type': 'application/json',
            "Version": "2021-07-28",

        }

        # if job_contact.get("mobile",""):
        #     contact1 = get_ghl_contacts(LOCATION_ID, f"%2B61{job_contact.get("mobile")}", ghl_token)
        # if job_contact.get("phone",""):
        #     contact2 = get_ghl_contacts(LOCATION_ID, f"%2B61{job_contact.get("phone")}", ghl_token)
        # contact_id = False
        # if contact2 or contact1:
        #     contact_id = contact1["contacts"] or contact2["contacts"]

        # print("existing contact id from update contact: ", contact_id)

        name_parts = client.name.split(" ",1)
        full_name = client.name
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
    
        payload = {
            "name": full_name,
            "firstName": first_name,
            "lastName": last_name,
            "address1": client_data.get('address_street', ''),
            "city": client_data.get('address_city', ''),
            "state": client_data.get('address_state', ''),
            "email":client.email,
            "postalCode": client_data.get('address_postcode', ''),
        }

        if client_data.get("job_is_scheduled_until_stamp") != "0000-00-00 00:00:00":
            job_date = datetime.strptime(client_data["job_is_scheduled_until_stamp"], "%Y-%m-%d %H:%M:%S")
            formatted_date = job_date.strftime("%d-%b-%Y %I:%M %p").upper()

            
            payload["customFields"] =  [{
                "id": "3Fd9Deng6jrRwuCPSfd0",
                "field_value": formatted_date
            }]
        
        
        payload["tags"] = ["ServiceM8"]

    

        print("ghl updata contact details:------------------ ", payload)
        
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()

        
        return response.json().get('contact')
    except Exception as e:
        print(f"Error updating contact in GoHighLevel: {str(e)}")
        return None


    

def update_ghl_opportunity(opportunity_id, job_data, client_obj, ghl_token):
    """Update existing opportunity in GoHighLevel with ServiceM8 job data"""

    print("oppertunity id: ", opportunity_id)
    
    url = f"https://services.leadconnectorhq.com/opportunities/{opportunity_id}"
    headers = {
        'Authorization': f'Bearer {ghl_token}',
        'Content-Type': 'application/json',
        "Version": "2021-07-28"

    }
    pipline_stage_id = False
    if job_data.get("status") == "Quote":
        pipline_stage_id = get_pipeline_stage_id_for_quote(job_data.get("quote_sent"), job_data.get("quote_sent_stamp"), job_data.get("job_is_scheduled_until_stamp"))
    
    payload = {
        "pipelineId": "kSt63A9h2lw1LL1cp7Hx",
        "name": f"{client_obj.name} - #{job_data.get("generated_job_id", "Updated Job")}",
        "status": map_servicem8_status_to_ghl(job_data.get("status", "open")),
        "pipelineStageId":pipline_stage_id if pipline_stage_id else map_servicem8_status_to_ghl_pipeline(job_data.get("status","d417fa3f-52df-426d-895b-4b9cfb0cfabf")),
        "contactId": client_obj.ghl_id,
        "monetaryValue": job_data.get("total_invoice_amount", 0),
        "source":job_data.get("category_name", "serviceM8"),
        "customFields": [
                {
                    "id": "b7zOencMXS3P6rgtiJqU", #street address
                    "field_value": job_data.get("job_address","")
                },
                {
                    "id": "2MZf3im3WK6dh5zklDi7", # Job description
                    "field_value": job_data.get("job_description","")
                }
        ],
    }

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("updation completed in job")
        return response.json()
    print("updation failed")
    
    return None

        


# handle_refresh()





def get_ghl_contacts(location_id, phone_number, access_token):
    print("ph number ph number",phone_number)
    url = f"https://services.leadconnectorhq.com/contacts/?locationId={location_id}&query={phone_number}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    
    response = requests.get(url, headers=headers)

    print("response: ", response.json())
    
    if response.status_code == 200:
        return response.json()  # Return JSON response if successful
    else:
        return {"error": response.status_code, "message": response.text}
