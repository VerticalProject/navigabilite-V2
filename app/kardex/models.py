from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from fleet.models import Aircraft


class Engine(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name="engines")

    name = models.CharField("Désignation", max_length=120, blank=True)
    manufacturer = models.CharField("Constructeur", max_length=120, blank=True)
    model = models.CharField("Modèle", max_length=120, blank=True)

    serial_number = models.CharField("N° de série", max_length=120, blank=True)
    part_number = models.CharField("Part Number", max_length=120, blank=True)

    initial_minutes = models.PositiveIntegerField("Heures initiales (minutes)", default=0)
    initial_cycles = models.PositiveIntegerField("Cycles initiaux", default=0)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["aircraft__registration", "id"]

    def __str__(self):
        base = self.name or "Moteur"
        return f"{self.aircraft.registration} - {base} ({self.serial_number or 'SN ?'})"


class EngineLog(models.Model):
    """Journal moteur : totalise heures/cycles moteur indépendamment de la cellule."""
    engine = models.ForeignKey(Engine, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField("Date")
    duration_minutes = models.PositiveIntegerField("Durée (minutes)")
    cycles = models.PositiveSmallIntegerField("Cycles", default=0)
    remarks = models.TextField("Remarques", blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.engine} {self.date} {self.duration_minutes} min / {self.cycles} cy"


class Component(models.Model):
    class Category(models.TextChoices):
        AIRFRAME = "airframe", "Cellule"
        ENGINE = "engine", "Moteur"
        PROPELLER = "propeller", "Hélice"
        AVIONICS = "avionics", "Avionique"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        STOCK = "stock", "En stock"
        INSTALLED = "installed", "Installé"
        IN_SHOP = "in_shop", "En maintenance"
        SCRAPPED = "scrapped", "Réformé"

    category = models.CharField("Catégorie", max_length=20, choices=Category.choices, default=Category.OTHER)

    # ✅ Nouveau : ATA
    ata = models.CharField("ATA", max_length=10, blank=True, db_index=True, help_text="Ex: 24, 32, 52...")

    name = models.CharField("Désignation", max_length=160)
    manufacturer = models.CharField("Constructeur", max_length=120, blank=True)
    part_number = models.CharField("Part Number", max_length=120, blank=True)
    serial_number = models.CharField("Serial Number", max_length=120, blank=True)

    initial_tsn_minutes = models.PositiveIntegerField("TSN initial (minutes)", default=0)
    initial_csn_cycles = models.PositiveIntegerField("CSN initial (cycles)", default=0)

    limit_minutes = models.PositiveIntegerField("Limite (minutes)", default=0)
    limit_cycles = models.PositiveIntegerField("Limite (cycles)", default=0)

    status = models.CharField("Statut", max_length=20, choices=Status.choices, default=Status.STOCK)

    installed_aircraft = models.ForeignKey(
        Aircraft, on_delete=models.SET_NULL, null=True, blank=True, related_name="installed_components"
    )
    installed_engine = models.ForeignKey(
        "kardex.Engine", on_delete=models.SET_NULL, null=True, blank=True, related_name="installed_components"
    )
    installed_position = models.CharField("Position / emplacement", max_length=120, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "serial_number", "part_number"]

    def clean(self):
        if self.installed_aircraft is not None and self.installed_engine is not None:
            raise ValidationError("Un composant ne peut pas être installé sur Aircraft ET Engine en même temps.")

    def __str__(self):
        sn = f" SN:{self.serial_number}" if self.serial_number else ""
        pn = f" PN:{self.part_number}" if self.part_number else ""
        return f"{self.name}{pn}{sn}"

    @property
    def current_location_str(self) -> str:
        if self.status == self.Status.INSTALLED:
            if self.installed_engine:
                return f"Installé sur {self.installed_engine} ({self.installed_position or '—'})"
            if self.installed_aircraft:
                return f"Installé sur {self.installed_aircraft.registration} ({self.installed_position or '—'})"
            return "Installé (cible inconnue)"
        if self.status == self.Status.IN_SHOP:
            return "En maintenance"
        if self.status == self.Status.SCRAPPED:
            return "Réformé"
        return "En stock"


class KardexEntry(models.Model):
    class Action(models.TextChoices):
        INSTALL = "install", "Installation"
        REMOVE = "remove", "Dépose"
        SEND_SHOP = "send_shop", "Envoi maintenance"
        RETURN_SHOP = "return_shop", "Retour maintenance"
        INSPECT = "inspect", "Inspection"
        OVERHAUL = "overhaul", "Révision"
        SCRAP = "scrap", "Réforme"

    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name="entries")

    action = models.CharField("Action", max_length=20, choices=Action.choices)
    date = models.DateField("Date")

    aircraft = models.ForeignKey(Aircraft, on_delete=models.SET_NULL, null=True, blank=True, related_name="kardex_entries")
    engine = models.ForeignKey(Engine, on_delete=models.SET_NULL, null=True, blank=True, related_name="kardex_entries")

    position = models.CharField("Position / emplacement", max_length=120, blank=True)

    at_minutes = models.PositiveIntegerField("Total (minutes) au moment de l’action", default=0)
    at_cycles = models.PositiveIntegerField("Total (cycles) au moment de l’action", default=0)

    workorder_ref = models.CharField("Référence doc / WO", max_length=120, blank=True)
    remarks = models.TextField("Remarques", blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def clean(self):
        if self.aircraft is not None and self.engine is not None:
            raise ValidationError("Choisis soit Aircraft, soit Engine (pas les deux).")
        if self.action in {self.Action.INSTALL, self.Action.REMOVE}:
            if self.aircraft is None and self.engine is None:
                raise ValidationError("Pour INSTALL/REMOVE, il faut cibler un Aircraft ou un Engine.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        comp = self.component

        if self.action == self.Action.INSTALL:
            comp.status = Component.Status.INSTALLED
            comp.installed_aircraft = self.aircraft
            comp.installed_engine = self.engine
            comp.installed_position = self.position or ""

        elif self.action == self.Action.REMOVE:
            comp.status = Component.Status.STOCK
            comp.installed_aircraft = None
            comp.installed_engine = None
            comp.installed_position = ""

        elif self.action == self.Action.SEND_SHOP:
            comp.status = Component.Status.IN_SHOP
            comp.installed_aircraft = None
            comp.installed_engine = None
            comp.installed_position = ""

        elif self.action == self.Action.RETURN_SHOP:
            comp.status = Component.Status.STOCK
            comp.installed_aircraft = None
            comp.installed_engine = None
            comp.installed_position = ""

        elif self.action == self.Action.SCRAP:
            comp.status = Component.Status.SCRAPPED
            comp.installed_aircraft = None
            comp.installed_engine = None
            comp.installed_position = ""

        comp.full_clean()
        comp.save(update_fields=["status", "installed_aircraft", "installed_engine", "installed_position", "updated_at"])

    def __str__(self):
        target = self.engine or self.aircraft
        tgt = str(target) if target else "—"
        return f"{self.get_action_display()} {self.component} @ {tgt} ({self.date})"
