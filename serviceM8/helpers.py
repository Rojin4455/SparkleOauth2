import re

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


def map_servicem8_status_to_ghl_pipeline_for_reactivation(status):
    status_mapping = {
        "Quote": "3a8236e9-07f8-4d8c-8782-6ec6f8e71a12",
        "Work Order": "925e5fbe-cb2c-46c2-95c3-77cea1320e84",  # quot sent id "5b2386b8-7bcd-41b2-879b-f1d9d04ea464",
        "Completed": "925e5fbe-cb2c-46c2-95c3-77cea1320e84",
        "Unsuccessful": "83876a1d-8850-4bea-a8d3-37b63971a083"
    }

    return status_mapping.get(status, "3a8236e9-07f8-4d8c-8782-6ec6f8e71a12")


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



def get_pipeline_stage_id_quote_for_reactivaton(quote_sent, quote_sent_stamp, job_is_scheduled_until_stamp):
    new_lead_id = "3a8236e9-07f8-4d8c-8782-6ec6f8e71a12"  # New Lead
    quote_booked_id = "331d51aa-ba76-48d9-85b5-16c121e66aef"  # Quote Booked
    quote_sent_id = "0efed6c9-f0e3-4acd-9c87-a05f070dbc8a"  # Quote Sent

    if job_is_scheduled_until_stamp == "0000-00-00 00:00:00":
        if quote_sent and quote_sent_stamp != "0000-00-00 00:00:00":
            return quote_sent_id  # Quote Sent
        return new_lead_id  # New Lead

    if job_is_scheduled_until_stamp != "0000-00-00 00:00:00":
        # if quote_sent and quote_sent_stamp != "0000-00-00 00:00:00":
        #     return quote_sent_id  # Quote Sent
        return quote_booked_id  # Quote Booked

    return None




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
    return f"+61{number}"



def format_datetime(datetime_obj, timezone_offset="+11:00"):
    try:
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S") + timezone_offset

    except ValueError as e:
        print(f"Error formatting datetime: {str(e)}")
       



# Function to get GHL contact ID by UUID
def get_ghl_id_by_uuid(user_uuid):
    uuid_to_ghl = {
    "938a4bc9-ee0a-4382-b9e4-229019b400cb": "4q6V9cppijdsjzrLyDOu",  # Nick
    "5642bafd-d2a1-404a-af2c-20178310a69b": "MPtQvLQmhq0HHCz9492d",  # Antonio
    "f20b8b22-20fa-4b0b-b740-2275c58f871b": "qgulhaNuualv53CscFox",  # Ramses
    "d8924764-b277-4200-81ab-2266edde371b": "yutodLOpS2yMt7q4ntLD",  # Santhosh
    "0c7c29ed-617b-4d60-9545-20188119ee0b": "0qQi4zcCXxqowZjWszKE",  # Simon
    }
    
    return uuid_to_ghl.get(user_uuid,"MPtQvLQmhq0HHCz9492d")