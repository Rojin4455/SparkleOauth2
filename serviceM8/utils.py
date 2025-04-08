import requests
from serviceM8.models import Job, Client, ServiceM8Token, JobAppointment
from accounts.models import GHLAuthCredentials
from serviceM8.services import get_opportunity, get_ghl_contacts, get_job_activity
from serviceM8.helpers import map_servicem8_status_to_ghl, get_ghl_id_by_uuid,map_servicem8_status_to_ghl_pipeline, map_servicem8_status_to_ghl_pipeline_for_reactivation, get_pipeline_stage_id_for_quote, get_pipeline_stage_id_quote_for_reactivaton, format_phone_number, format_datetime

LOCATION_ID = "zPbyOYoNWW8AzKRkMekd"


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
        contact_result = update_ghl_contact(client, client_data, ghl_token, job_contact)
        if contact_result:
            client.tags = contact_result.get("tags")
            client.save()
        return client
    
    contact_result = create_ghl_contact(client, client_data, ghl_token, job_contact)
    print("results of contact create:",contact_result)
    if contact_result and contact_result.get("id"):
        client.ghl_id = contact_result.get("id")
        client.tags = contact_result.get("tags")
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
    
    oppertunities = get_opportunity(f"#{job_data.get("generated_job_id")}")
    
    if oppertunities and oppertunities.get("opportunities"):
        oppertunity = oppertunities.get("opportunities")[0]
        update_ghl_opportunity(oppertunity.get("id"), job_data, client_obj ,ghl_token)
        job.ghl_id = oppertunity.get("id")
        job.save()
        return job
    else:

        opportunity_result = create_ghl_opportunity(job_data,client_obj, ghl_token)
        if opportunity_result and opportunity_result.get("id"):
            job.ghl_id = opportunity_result.get("id")
            job.save()
        return job




def create_ghl_opportunity(job_data, client_obj, ghl_token):
    """Create an opportunity in GoHighLevel based on ServiceM8 job data"""
    try:
        ghl_api_url = "https://services.leadconnectorhq.com/opportunities/"
        headers = {
            "Authorization": f"Bearer {ghl_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        
        pipeline_id = "kSt63A9h2lw1LL1cp7Hx"
        
        pipeline_stage_id = None
        status = job_data.get("status")
        
        if status == "Quote":
            # if is_reactivation:
            #     pipeline_stage_id = get_pipeline_stage_id_quote_for_reactivaton(
            #         job_data.get("quote_sent"),
            #         job_data.get("quote_sent_stamp"),
            #         job_data.get("job_is_scheduled_until_stamp")
            #     )
            # else:
            pipeline_stage_id = get_pipeline_stage_id_for_quote(
                job_data.get("quote_sent"),
                job_data.get("quote_sent_stamp"),
                job_data.get("job_is_scheduled_until_stamp")
            )
        else:
            default_status = "d417fa3f-52df-426d-895b-4b9cfb0cfabf"
            job_status = job_data.get("status", default_status)
            
            # if is_reactivation:
            #     pipeline_stage_id = map_servicem8_status_to_ghl_pipeline_for_reactivation(job_status)
            # else:
            pipeline_stage_id = map_servicem8_status_to_ghl_pipeline(job_status)
        
        payload = {
            "name": f"{client_obj.name} - #{job_data.get('generated_job_id', 'New Job')}",
            "locationId": LOCATION_ID,
            "status": map_servicem8_status_to_ghl(job_data.get("status", "open")),
            "pipelineId": pipeline_id,
            "pipelineStageId": pipeline_stage_id,
            "contactId": client_obj.ghl_id,
            "monetaryValue": job_data.get("total_invoice_amount", 0),
            "source": job_data.get("category_name", "serviceM8"),
            "customFields": [
                {
                    "id": "b7zOencMXS3P6rgtiJqU",
                    "field_value": job_data.get("job_address", "")
                },
                {
                    "id": "2MZf3im3WK6dh5zklDi7",
                    "field_value": job_data.get("job_description", "")
                }
            ],
        }
        
        response = requests.post(ghl_api_url, headers=headers, json=payload)
        print("oppertunity created status code ;", response.status_code)
        response.raise_for_status()
        
        if response.status_code == 201:
            return response.json().get("opportunity", [])
        return None
        
    except Exception as e:
        print(f"Error creating opportunity in GoHighLevel: {str(e)}")
        return None



def create_ghl_contact(client, client_data, ghl_token, job_contact):
    """Create or update a contact in GoHighLevel from ServiceM8 client data"""
    from datetime import datetime
    try:
        # Normalize phone numbers
        mobile = format_phone_number(job_contact.get("mobile",""))
        phone = format_phone_number(job_contact.get("phone",""))
        
        
        # Initialize contact as None
        contact = None

        # print("client data: --------------------------------------", client_data)
        # print("job contact data: --------------------------------------", job_contact)
        
        # Try to find existing contact by mobile or phone
        if mobile:
            contact = get_ghl_contacts(LOCATION_ID, mobile, ghl_token)

        # Only proceed to check phone if no contacts found yet
        if not contact or not contact.get('contacts'):
            if phone:
                contact = get_ghl_contacts(LOCATION_ID, phone, ghl_token)

        # Only proceed to check email if still no contacts found
        if not contact or not contact.get('contacts'):
            if job_contact.get("email", ""):
                contact = get_ghl_contacts(LOCATION_ID, job_contact.get("email"), ghl_token)
                
        print("contact is here: -------------------------------",contact)
        
        name_parts = client.name.split(" ", 1)
        full_name = client.name
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        base_payload = {"tags":["servicem8"]}

        if first_name:
            base_payload["firstName"] = first_name
        if full_name:
            base_payload["name"] = full_name
        if last_name:
            base_payload["lastName"] = last_name
        if client_data.get('address_street', ''):
            base_payload["address1"] = client_data.get('address_street')

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
            base_payload["tags"] += existing_contact.get("tags")
            if not existing_contact.get('email'):
                email_contact = get_ghl_contacts(LOCATION_ID, job_contact.get("email"), ghl_token)
                if email_contact and not email_contact.get("contacts"):
                    base_payload['email'] = job_contact.get("email")
            if not existing_contact.get("phone"):
                phone_contact = get_ghl_contacts(LOCATION_ID, job_contact.get("phone"), ghl_token)
                if phone_contact and not phone_contact.get("contacts"):
                    base_payload["phone"] = job_contact.get("phone")

            print("base payload: ,", base_payload)
            
            # Use PUT for update
            print("contact updated in created method")
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
            if job_contact.get("mobile", "") or job_contact.get("phone",""):
                base_payload["phone"] = job_contact.get("mobile", "") or job_contact.get("phone","")
            if job_contact.get("email", ""):
                base_payload['email'] = job_contact.get("email")
            base_payload.update({
                "locationId": LOCATION_ID
            })

            print("create client")
            
            # Use POST for new contact
            response = requests.post(url, 
                headers={
                    'Authorization': f'Bearer {ghl_token}',
                    'Content-Type': 'application/json',
                    "Version": "2021-07-28",
                }, 
                json=base_payload
            )
        
        response.raise_for_status()
        return response.json().get('contact')
    
    except requests.exceptions.RequestException as e:
        print("final base payload: ", base_payload)
        print(f"Error creating/updating contact: {e}")
        return None


def update_ghl_contact(client, client_data, ghl_token, job_contact):
    from datetime import datetime
    import requests

    """Update existing contact in GoHighLevel with ServiceM8 client data, but only updating changed fields"""
    try:
        # First, fetch the current contact data from GoHighLevel
        fetch_url = f"https://services.leadconnectorhq.com/contacts/{client.ghl_id}"
        headers = {
            'Authorization': f'Bearer {ghl_token}',
            'Content-Type': 'application/json',
            "Version": "2021-07-28",
        }

        # Get current contact data
        fetch_response = requests.get(fetch_url, headers=headers)
        fetch_response.raise_for_status()
        current_contact = fetch_response.json().get('contact', {})
        
        if not current_contact:
            print(f"Contact with ID {client.ghl_id} not found in GoHighLevel")
            return None

        # Prepare new data
        name_parts = client.name.split(" ", 1)
        full_name = client.name
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Initialize payload with only fields that have changed
        payload = {}
        
        # Check and update name if changed
        if current_contact.get('name') != full_name:
            payload['name'] = full_name
        
        if current_contact.get('firstName') != first_name:
            payload['firstName'] = first_name
            
        if current_contact.get('lastName') != last_name:
            payload['lastName'] = last_name
            
        # Check and update address fields if changed
        if current_contact.get('address1') != client_data.get('address_street', ''):
            payload['address1'] = client_data.get('address_street', '')
            
        if current_contact.get('city') != client_data.get('address_city', ''):
            payload['city'] = client_data.get('address_city', '')
            
        if current_contact.get('state') != client_data.get('address_state', ''):
            payload['state'] = client_data.get('address_state', '')
            
        if current_contact.get('email') != client.email:
            payload['email'] = client.email
            
        if current_contact.get('postalCode') != client_data.get('address_postcode', ''):
            payload['postalCode'] = client_data.get('address_postcode', '')

        # Handle custom fields - scheduled date
        if client_data.get("job_is_scheduled_until_stamp") != "0000-00-00 00:00:00":
            job_date = datetime.strptime(client_data["job_is_scheduled_until_stamp"], "%Y-%m-%d %H:%M:%S")
            formatted_date = job_date.strftime("%d-%b-%Y %I:%M %p").upper()
            
            # Check if custom field exists and needs updating
            current_custom_fields = current_contact.get('customFields', [])
            schedule_field_exists = False
            schedule_field_updated = False
            
            for field in current_custom_fields:
                if field.get('id') == "3Fd9Deng6jrRwuCPSfd0":
                    schedule_field_exists = True
                    if field.get('field_value') != formatted_date:
                        schedule_field_updated = True
                    break
            
            if schedule_field_updated or not schedule_field_exists:
                payload["customFields"] = [{
                    "id": "3Fd9Deng6jrRwuCPSfd0",
                    "field_value": formatted_date
                }]
        
        # Always ensure ServiceM8 tag exists
        current_tags = current_contact.get('tags', [])
        if "servicem8" not in current_tags:
            payload["tags"] = current_tags + ["servicem8"]
        
        # If no changes detected, return current contact
        if not payload:
            print("No changes detected for contact in GoHighLevel")
            return current_contact
        
        # Update contact with changed fields only
        print("Updating GoHighLevel contact with changes: ", payload)
        update_url = f"https://services.leadconnectorhq.com/contacts/{client.ghl_id}"
        update_response = requests.put(update_url, headers=headers, json=payload)
        update_response.raise_for_status()
        

        return update_response.json().get('contact')
    
    except Exception as e:
        print(f"Error updating contact in GoHighLevel: {str(e)}")
        return None


    

def update_ghl_opportunity(opportunity_id, job_data, client_obj, ghl_token):
    """Update existing opportunity in GoHighLevel with ServiceM8 job data"""
    try:
        # First, fetch the current opportunity data
        fetch_url = f"https://services.leadconnectorhq.com/opportunities/{opportunity_id}"
        headers = {
            'Authorization': f'Bearer {ghl_token}',
            'Content-Type': 'application/json',
            "Version": "2021-07-28"
        }
        
        # Get current opportunity data
        fetch_response = requests.get(fetch_url, headers=headers)
        fetch_response.raise_for_status()
        current_opportunity = fetch_response.json().get('opportunity', {})
        
        if not current_opportunity:
            print(f"Opportunity with ID {opportunity_id} not found in GoHighLevel")
            return None
            
        # Determine pipeline details
        # is_reactivation = "client reactivation" in client_obj.tags
        pipeline_id = "kSt63A9h2lw1LL1cp7Hx"
        
        # Determine pipeline stage ID based on job status and client tags
        pipeline_stage_id = None
        status = job_data.get("status")
        
        if status == "Quote":
            # if is_reactivation:
            #     pipeline_stage_id = get_pipeline_stage_id_quote_for_reactivaton(
            #         job_data.get("quote_sent"),
            #         job_data.get("quote_sent_stamp"),
            #         job_data.get("job_is_scheduled_until_stamp")
            #     )
            # else:
            pipeline_stage_id = get_pipeline_stage_id_for_quote(
                job_data.get("quote_sent"),
                job_data.get("quote_sent_stamp"),
                job_data.get("job_is_scheduled_until_stamp")
            )
        else:
            # Default fallback status IDs if not provided
            default_status = "d417fa3f-52df-426d-895b-4b9cfb0cfabf"
            job_status = job_data.get("status", default_status)
            
            pipeline_stage_id = map_servicem8_status_to_ghl_pipeline(job_status)
        
        payload = {}
        
        new_name = f"{client_obj.name} - #{job_data.get('generated_job_id', 'Updated Job')}"
        if current_opportunity.get('name') != new_name:
            payload['name'] = new_name
            
        if current_opportunity.get('pipelineId') != pipeline_id:
            payload['pipelineId'] = pipeline_id
            
        new_status = map_servicem8_status_to_ghl(job_data.get("status", "open"))
        if current_opportunity.get('status') != new_status:
            payload['status'] = new_status
            
        if current_opportunity.get('pipelineStageId') != pipeline_stage_id:
            payload['pipelineStageId'] = pipeline_stage_id
            
        if current_opportunity.get('contactId') != client_obj.ghl_id:
            payload['contactId'] = client_obj.ghl_id
            
        new_monetary_value = job_data.get("total_invoice_amount", 0)
        if current_opportunity.get('monetaryValue') != new_monetary_value:
            payload['monetaryValue'] = new_monetary_value
            
        # Source
        if job_data.get("category_name"):
            payload['source'] = job_data.get("category_name")
        # new_source = job_data.get("category_name", "serviceM8")
        # if current_opportunity.get('source') != new_source:
        #     payload['source'] = new_source
            
        current_custom_fields = {field.get('id'): field.get('field_value') for field in current_opportunity.get('customFields', [])}
        
        new_custom_fields = [
            {
                "id": "b7zOencMXS3P6rgtiJqU",  # street address
                "field_value": job_data.get("job_address", "")
            },
            {
                "id": "2MZf3im3WK6dh5zklDi7",  # Job description
                "field_value": job_data.get("job_description", "")
            }
        ]
        
        # Check if custom fields have changed
        custom_fields_changed = False
        for field in new_custom_fields:
            if field['id'] not in current_custom_fields or current_custom_fields[field['id']] != field['field_value']:
                custom_fields_changed = True
                break
                
        if custom_fields_changed:
            payload['customFields'] = new_custom_fields
        
        # If no changes detected, return current opportunity
        if not payload:
            print("No changes detected for opportunity in GoHighLevel")
            return current_opportunity
            
        # Update opportunity with changed fields only
        print("Updating GoHighLevel opportunity with changes: ", payload)
        update_response = requests.put(fetch_url, headers=headers, json=payload)
        update_response.raise_for_status()
        
        if update_response.status_code == 200:
            print("Update completed successfully")
            return update_response.json()
        
        print("Update failed with status code:", update_response.status_code)
        return None
        
    except Exception as e:
        print(f"Error updating opportunity in GoHighLevel: {str(e)}")
        return None



def update_or_create_appointment(job_data):
    from datetime import datetime,timedelta

    try:
        job_uuid = job_data.get("uuid")
        if not job_uuid:
            print("Error: No job UUID provided")
            return None
            
        token = ServiceM8Token.objects.first()
        ghl_token = GHLAuthCredentials.objects.first()
        if not token or not token.access_token:
            print("Error: ServiceM8 token not found")
            return None
        if not ghl_token or not ghl_token.access_token:
            print("Error: GHL token not found")
            return None
            
        # Get job activity from ServiceM8
        servicem8_appointment = get_job_activity(token.access_token, job_uuid)
        if not servicem8_appointment:
            print(f"No job activity found for job UUID: {job_uuid}")
            return None
            
        start_date, end_date = servicem8_appointment.get("start_date"), servicem8_appointment.get("end_date")
        if not start_date or not end_date:
            print("Error: Start date or end date missing from ServiceM8 job activity")
            return None
        
        # Get associated Job object
        try:
            job_obj = Job.objects.get(uuid=job_uuid)
        except Job.DoesNotExist:
            print(f"Error: Job with UUID {job_uuid} not found in database")
            return None
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        adjusted_start_dt = start_dt + timedelta(hours=1)
        adjusted_end_dt = end_dt + timedelta(hours=1)
        
        formatted_start = format_datetime(adjusted_start_dt)
        formatted_end = format_datetime(adjusted_end_dt)
        start_date = datetime.fromisoformat(formatted_start)
        end_date = datetime.fromisoformat(formatted_end)
        
        try:
            # Try to find existing appointment
            job_appointment_obj = JobAppointment.objects.get(job=job_obj)
            
            # Update existing appointment in GoHighLevel
            status_code, response_data = update_appointment(
                servicem8_appointment.get("staff_uuid"),
                job_appointment_obj.ghl_id, 
                formatted_start, 
                formatted_end, 
                ghl_token.access_token
            )
            
            # Update local record
            job_appointment_obj.start_date = start_date
            job_appointment_obj.end_date = end_date
            job_appointment_obj.save()
            
            print(f"Updated appointment for job {job_uuid} with GoHighLevel ID {job_appointment_obj.ghl_id}")
            return status_code, response_data
            
        except JobAppointment.DoesNotExist:
            # Create new appointment in GoHighLevel
            status_code, response_data = create_appointment(
                servicem8_appointment.get("staff_uuid"),
                job_data,
                formatted_start, 
                formatted_end, 
                ghl_token.access_token
            )
            
            if status_code == 201 and response_data.get('id'):
                # Save new appointment in database
                JobAppointment.objects.create(
                    uuid=servicem8_appointment.get("uuid"),
                    ghl_id=response_data['id'],
                    job=job_obj,
                    start_date=start_date,
                    end_date=end_date
                )
                print(f"Created new appointment for job {job_uuid} with GoHighLevel ID {response_data['id']}")
            else:
                print(f"Failed to create appointment in GoHighLevel: {status_code} - {response_data}")
                
            return status_code, response_data
    
    except Exception as e:
        print(f"Error in update_or_create_appointment: {str(e)}")
        return None





def create_appointment(staff_uuid, job_data, start_date, end_date, token):
    """
    Creates a new appointment in GoHighLevel.
    
    Args:
        job_data (dict): Job data including contact ID
        start_date (str): Formatted start datetime
        end_date (str): Formatted end datetime
        token (str): GoHighLevel access token
        
    Returns:
        tuple: (status_code, response_data)
    """
    try:
        url = "https://services.leadconnectorhq.com/calendars/events/appointments"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            'Content-Type': 'application/json',
            "Version": "2021-07-28",
        }
        assigned_userid = get_ghl_id_by_uuid(staff_uuid)
        

        data = {
            "calendarId": "URbFzsBiWyDsC0rp2xaQ",
            "locationId": "zPbyOYoNWW8AzKRkMekd",
            "contactId": job_data.get('contact_id'),
            "startTime": start_date,
            "endTime": end_date,
            "skipAvailabilityCheck": True,
            "toNotify":True,
            "ignoreDateRange": True
        }
        if assigned_userid:
            data["assignedUserId"] = assigned_userid

        print("data in create appointment----------------------> ", data)

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        print(f"Appointment created in GoHighLevel: {response.status_code}")
        return response.status_code, response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating appointment in GoHighLevel: {str(e)}")
        if hasattr(e, 'response') and e.response:
            return e.response.status_code, e.response.json()
        return 500, {"error": str(e)}


def update_appointment(staff_uuid, appointment_id, start_time, end_time, token):

    try:
        fetch_url = f"https://services.leadconnectorhq.com/calendars/events/appointments/{appointment_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Version": "2021-04-15"
        }
        
        fetch_response = requests.get(fetch_url, headers=headers)
        fetch_response.raise_for_status()
        current_appointment = fetch_response.json()
        
        if not current_appointment:
            print(f"Appointment with ID {appointment_id} not found in GoHighLevel")
            return 404, {"error": "Appointment not found"}
        
        payload = {}

        assigned_userid = get_ghl_id_by_uuid(staff_uuid)
        if assigned_userid:
            if current_appointment.get("assignedUserId") != assigned_userid:
                payload['assignedUserId'] = assigned_userid
        
        if current_appointment.get('startTime') != start_time:
            payload['startTime'] = start_time
            
        if current_appointment.get('endTime') != end_time:
            payload['endTime'] = end_time
            
        if not payload:
            print("No changes detected for appointment in GoHighLevel")
            return 200, {"appointment": current_appointment}
        
        print("update payload:", payload)
        update_url = f"https://services.leadconnectorhq.com/calendars/events/appointments/{appointment_id}"
        update_response = requests.put(update_url, headers=headers, json=payload)
        update_response.raise_for_status()
        
        print(f"Appointment updated in GoHighLevel: {update_response.status_code}")
        return update_response.status_code, update_response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error updating appointment in GoHighLevel: {str(e)}")
        if hasattr(e, 'response') and e.response:
            return e.response.status_code, e.response.json()
        return 500, {"error": str(e)}






