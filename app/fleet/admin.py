from django.contrib import admin
from .models import Aircraft

@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ("registration", "manufacturer", "model", "category", "organization", "owner_user")
    search_fields = ("registration", "manufacturer", "model", "serial_number")
    list_filter = ("category", "organization")
