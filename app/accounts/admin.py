from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Rôle et Organisation", {"fields": ("role", "organization")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "organization", "is_staff", "is_superuser")
    list_filter = ("role", "organization", "is_staff", "is_superuser")
