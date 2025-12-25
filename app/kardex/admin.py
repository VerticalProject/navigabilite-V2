from django.contrib import admin
from .models import Engine, Component, KardexEntry


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    list_display = ("aircraft", "name", "manufacturer", "model", "serial_number", "part_number", "active")
    list_filter = ("active", "manufacturer", "model")
    search_fields = ("aircraft__registration", "name", "serial_number", "part_number")


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "manufacturer", "part_number", "serial_number", "status", "current_location_str")
    list_filter = ("category", "manufacturer", "status")
    search_fields = ("name", "part_number", "serial_number")


@admin.register(KardexEntry)
class KardexEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "action", "component", "aircraft", "engine", "position", "at_minutes", "at_cycles", "workorder_ref")
    list_filter = ("action", "date")
    search_fields = ("component__name", "component__serial_number", "component__part_number", "workorder_ref", "position")
