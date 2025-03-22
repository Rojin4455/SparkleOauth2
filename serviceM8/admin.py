from django.contrib import admin
from serviceM8.models import ServiceM8Log, Client, Job
import json

@admin.register(ServiceM8Log)
class ServiceM8LogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'event_type', 'status', 'job_uuid', 'client_uuid', 'job_link_successful', 'client_link_successful')
    list_filter = ('status', 'event_type', 'job_link_successful', 'client_link_successful', 'timestamp')
    search_fields = ('job_uuid', 'client_uuid', 'error_message', 'servicem8_data')
    readonly_fields = ('timestamp', 'get_servicem8_data_display')
    
    def get_servicem8_data_display(self, obj):
        # Format JSON for better display in admin
        try:
            data = obj.get_servicem8_data()
            return json.dumps(data, indent=4)
        except:
            return obj.servicem8_data
    get_servicem8_data_display.short_description = "ServiceM8 Data"
    