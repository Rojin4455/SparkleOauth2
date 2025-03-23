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
        update_ghl_contact(client, client_data, ghl_token)
        return client
    
    contact_result = create_ghl_contact(client, client_data, ghl_token)
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
    payload = {
        "pipelineId":"kSt63A9h2lw1LL1cp7Hx",
        "name": f"{client_obj.name} - #{job_data.get("generated_job_id", "New Job")}",
        "locationId":LOCATION_ID,
        "status": map_servicem8_status_to_ghl(job_data.get("status", "open")),
        "pipelineStageId":map_servicem8_status_to_ghl_pipeline(job_data.get("status","d417fa3f-52df-426d-895b-4b9cfb0cfabf")),
        "contactId": client_obj.ghl_id,
        "monetaryValue": job_data.get("total_invoice_amount", 0),
        "source":"serviceM8",
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



def create_ghl_contact(client, client_data, ghl_token):
    """Create a new contact in GoHighLevel from ServiceM8 client data"""
    try:
        url = "https://services.leadconnectorhq.com/contacts/"
        
        headers = {
            'Authorization': f'Bearer {ghl_token}',
            'Content-Type': 'application/json',
            "Version": "2021-07-28",
        }
        
        name_parts = client.name.split(" ",1)
        full_name = client.name
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        payload = {
            "locationId": LOCATION_ID,
            "name":full_name,
            "firstName":first_name,
            "lastName": last_name,
            "phone":client.mobile,
            "email":client.email,
            "address1": client_data.get('address_street', ''),
            "source": "ServiceM8 Integration",
            "tags": ["ServiceM8"],
        }

            
        response = requests.post(url, headers=headers, json=payload,)
        response.raise_for_status()        
        return response.json().get('contact')
    except requests.exceptions.HTTPError as e:
        print(f"Error creating contact in GoHighLevel: {e}")
        if hasattr(e.response, 'text'):
            print(f"Error details: {e.response.text}")
        print(f"error something: ", e)
        raise
    except Exception as e:
        print(f"Error creating contact in GoHighLevel: {e}")
        raise

def update_ghl_contact(client,client_data, ghl_token):
    """Update existing contact in GoHighLevel with ServiceM8 client data"""
    try:
        url = f"https://services.leadconnectorhq.com/contacts/{client.ghl_id}"
        headers = {
            'Authorization': f'Bearer {ghl_token}',
            'Content-Type': 'application/json',
            "Version": "2021-07-28",

        }

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
            "phone":client.mobile,
            "email":client.email,
            "postalCode": client_data.get('address_postcode', ''),
        }
        
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
    
    payload = {
        "pipelineId": "kSt63A9h2lw1LL1cp7Hx",
        "name": f"{client_obj.name} - #{job_data.get("generated_job_id", "Updated Job")}",
        "status": map_servicem8_status_to_ghl(job_data.get("status", "open")),
        "pipelineStageId":map_servicem8_status_to_ghl_pipeline(job_data.get("status","d417fa3f-52df-426d-895b-4b9cfb0cfabf")),
        "contactId": client_obj.ghl_id,
        "monetaryValue": job_data.get("total_invoice_amount", 0),
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



