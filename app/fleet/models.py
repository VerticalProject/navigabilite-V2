from django.db import models
from django.conf import settings
from accounts.models import Organization

class Aircraft(models.Model):
    class Category(models.TextChoices):
        ULM = "ULM", "ULM"
        SEP = "SEP", "Monomoteur piston (SEP)"
        MEP = "MEP", "Multimoteur piston (MEP)"

    registration = models.CharField("Immatriculation", max_length=20, unique=True)
    manufacturer = models.CharField("Constructeur", max_length=120, blank=True)
    model = models.CharField("Modèle", max_length=120, blank=True)
    category = models.CharField("Catégorie", max_length=8, choices=Category.choices, default=Category.SEP)
    mtow_kg = models.PositiveIntegerField("MTOW (kg)", null=True, blank=True)
    year = models.PositiveIntegerField("Année", null=True, blank=True)
    serial_number = models.CharField("N° de série", max_length=120, blank=True)

    initial_minutes = models.PositiveIntegerField("HDV initiales (minutes)", default=0)
    initial_cycles  = models.PositiveIntegerField("Cycles initiaux", default=0)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="aircraft")
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_aircraft")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registration"]

    def __str__(self):
        return self.registration


class FlightLog(models.Model):
    """Ligne de journal de vol (totalise HDV & cycles)."""
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField("Date")
    from_icao = models.CharField("Départ (ICAO/IATA)", max_length=8, blank=True)
    to_icao   = models.CharField("Arrivée (ICAO/IATA)", max_length=8, blank=True)
    duration_minutes = models.PositiveIntegerField("Durée (minutes)")
    cycles = models.PositiveSmallIntegerField("Cycles", default=1)
    pilot = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="flights")
    remarks = models.TextField("Remarques", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.aircraft.registration} {self.date} {self.duration_minutes} min / {self.cycles} cycle(s)"
    
class VisitRule(models.Model):
    """Règle de visite périodique (ex: 50h, 100h) spécifique à un aéronef."""
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name="visit_rules")
    name = models.CharField("Nom de la visite", max_length=120)  # ex: "50h", "100h"
    interval_minutes = models.PositiveIntegerField("Intervalle (minutes)", help_text="Ex: 50h = 3000")
    interval_cycles = models.PositiveIntegerField("Intervalle (cycles)", default=0, help_text="Optionnel (0 si non utilisé)")

    due_at_minutes = models.PositiveIntegerField("Échéance actuelle (minutes totales cellule)")
    due_at_cycles = models.PositiveIntegerField("Échéance actuelle (cycles totaux cellule)", default=0)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["aircraft", "name"]
        unique_together = [("aircraft", "name")]

    def __str__(self):
        return f"{self.aircraft.registration} - {self.name}"

class VisitCompletion(models.Model):
    """Historique des réalisations de visites (pour traçabilité)."""
    rule = models.ForeignKey(VisitRule, on_delete=models.CASCADE, related_name="completions")
    date = models.DateField("Date de réalisation")
    at_minutes = models.PositiveIntegerField("Minutes totales cellule (au moment de la réalisation)")
    at_cycles = models.PositiveIntegerField("Cycles totaux cellule (au moment de la réalisation)", default=0)
    remarks = models.TextField("Remarques", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.rule} @ {self.at_minutes} min"

