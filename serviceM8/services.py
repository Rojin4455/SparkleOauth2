import requests
import urllib.parse
from accounts.models import GHLAuthCredentials


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


def get_opportunity(oppertunity_id):
    token = GHLAuthCredentials.objects.first()
    print("reacehd oppertunity")
    url = "https://services.leadconnectorhq.com/opportunities/search"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token.access_token}",
        "Version": "2021-07-28"
    }
    params = {
        "q": oppertunity_id,
        "location_id": "zPbyOYoNWW8AzKRkMekd"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None
    


def get_ghl_contacts(location_id, number_or_email, access_token):
    print("ph number or email",number_or_email)
    url = f"https://services.leadconnectorhq.com/contacts/?locationId={location_id}&query={number_or_email}"
    
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
    

def get_job_activity(token, uuid):

    try:
        url = f"https://api.servicem8.com/api_1.0/jobactivity.json?%24filter=job_uuid%20eq%20{uuid}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {token}"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        activities = response.json()
        if not activities:
            print(f"No job activities found for job UUID: {uuid}")
            return None
            
        # Return the latest activity (last in the list)
        latest_activity = activities[-1]
        print(f"Latest job activity for job {uuid}: {latest_activity}")
        return latest_activity
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching job activity from ServiceM8: {str(e)}")
        return None
    except (IndexError, ValueError, KeyError) as e:
        print(f"Error processing job activity response: {str(e)}")
        return None
    


def get_staff_details(token, uuid):

    url = f"https://api.servicem8.com/api_1.0/staff/{uuid}.json"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()