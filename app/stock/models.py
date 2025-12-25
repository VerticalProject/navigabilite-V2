from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import secrets

from accounts.models import Organization


def _gen_barcode():
    # 12 chars alphanum, facile à taper / scanner
    return secrets.token_hex(6).upper()


class StockLocation(models.Model):
    """Magasin / emplacement (un site, un local, un magasin, etc.)"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_locations")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class StockItem(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_items")

    designation = models.CharField(max_length=180)
    pn = models.CharField(max_length=64, blank=True, default="")          # optionnel
    pn_mfr = models.CharField(max_length=64, blank=True, default="")      # PN constructeur optionnel
    ata = models.CharField(max_length=16, blank=True, default="")         # optionnel (ex: 21-00, 32, etc.)

    # Multi-magasin / multi-emplacement
    locations = models.ManyToManyField(StockLocation, blank=True, related_name="items")

    # Code barre (recherche rapide)
    barcode = models.CharField(max_length=32, unique=True, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["designation", "pn"]

    def save(self, *args, **kwargs):
        # Auto-génère un code barre si vide
        if not self.barcode:
            # boucle anti-collision
            for _ in range(10):
                code = _gen_barcode()
                if not StockItem.objects.filter(barcode=code).exists():
                    self.barcode = code
                    break
            if not self.barcode:
                raise ValidationError("Impossible de générer un code barre unique.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.designation
