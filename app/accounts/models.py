from django.db import models
from django.contrib.auth.models import AbstractUser


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Roles(models.TextChoices):
        PILOT = "pilote", "Pilote"
        TECHNICIAN = "technicien", "Technicien"
        OWNER = "proprietaire", "Propriétaire"
        CAMO = "camo", "CAMO"
        ADMIN = "admin", "Administrateur"
        SUPERADMIN = "superadmin", "Super administrateur"

    class UITheme(models.TextChoices):
        DARK = "dark", "Sombre"
        LIGHT = "light", "Clair"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.PILOT)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # ✅ Nouveau : thème UI par utilisateur
    ui_theme = models.CharField(max_length=10, choices=UITheme.choices, default=UITheme.DARK)

    def is_admin_or_super(self):
        return self.role in {self.Roles.ADMIN, self.Roles.SUPERADMIN}

    def is_super(self):
        return self.role == self.Roles.SUPERADMIN
