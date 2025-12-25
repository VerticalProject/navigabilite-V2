from django import forms
from django.contrib.auth import get_user_model
from accounts.models import Organization
from .models import Aircraft, FlightLog, VisitRule

User = get_user_model()


# ------------------------
# Helpers HH:MM <-> minutes
# ------------------------

def hhmm_to_minutes(value: str) -> int:
    """
    Accepts "H:MM" or "HH:MM" or "123:45" (hours can be > 24).
    """
    value = (value or "").strip()
    if not value:
        return 0

    if ":" not in value:
        raise forms.ValidationError("Format attendu HH:MM")

    parts = value.split(":")
    if len(parts) != 2:
        raise forms.ValidationError("Format attendu HH:MM")

    h_str, m_str = parts[0].strip(), parts[1].strip()
    if h_str == "" or m_str == "":
        raise forms.ValidationError("Format attendu HH:MM")

    try:
        h = int(h_str)
        m = int(m_str)
    except ValueError:
        raise forms.ValidationError("Format attendu HH:MM")

    if h < 0:
        raise forms.ValidationError("Heures invalides.")
    if m < 0 or m > 59:
        raise forms.ValidationError("Minutes invalides (00 à 59).")

    return h * 60 + m


def minutes_to_hhmm(minutes: int) -> str:
    minutes = int(minutes or 0)
    if minutes < 0:
        minutes = 0
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


# ------------------------
# Aircraft
# ------------------------

class AircraftForm(forms.ModelForm):
    # ✅ Saisie user en HH:MM
    initial_hhmm = forms.CharField(
        label="HDV initiales (HH:MM)",
        required=False,
        help_text="Ex : 1234:30",
        widget=forms.TextInput(attrs={"placeholder": "0:00"}),
    )

    class Meta:
        model = Aircraft
        fields = [
            "registration", "manufacturer", "model", "category",
            "mtow_kg", "year", "serial_number",
            "organization", "owner_user",
            "initial_cycles",
        ]
        widgets = {
            "initial_cycles": forms.NumberInput(attrs={"min": 0}),
            "mtow_kg": forms.NumberInput(attrs={"min": 0}),
            "year": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Organisation limitée si non superadmin
        if user and getattr(user, "role", None) != getattr(user, "Roles").SUPERADMIN:
            self.fields["organization"].queryset = Organization.objects.filter(id=user.organization_id)

        # Pré-remplissage HH:MM depuis minutes stockées
        if self.instance and self.instance.pk:
            self.fields["initial_hhmm"].initial = minutes_to_hhmm(self.instance.initial_minutes or 0)
        else:
            self.fields["initial_hhmm"].initial = "0:00"

    def clean_initial_hhmm(self):
        value = (self.cleaned_data.get("initial_hhmm") or "").strip()
        if value in ("", None):
            return 0
        return hhmm_to_minutes(value)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.initial_minutes = self.cleaned_data.get("initial_hhmm", 0)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


# ------------------------
# Flight log
# ------------------------

class FlightLogForm(forms.ModelForm):
    # ✅ Saisie user en HH:MM
    duration_hhmm = forms.CharField(
        label="Durée (HH:MM)",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "0:45"}),
    )

    class Meta:
        model = FlightLog
        fields = ["date", "from_icao", "to_icao", "cycles", "pilot", "remarks", "duration_hhmm"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "cycles": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si on édite un log existant (rare), on pré-remplit HH:MM
        if self.instance and self.instance.pk:
            self.fields["duration_hhmm"].initial = minutes_to_hhmm(self.instance.duration_minutes or 0)

    def clean_duration_hhmm(self):
        val = (self.cleaned_data.get("duration_hhmm") or "").strip()
        minutes = hhmm_to_minutes(val)
        if minutes <= 0:
            raise forms.ValidationError("La durée doit être > 0.")
        return minutes

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duration_minutes = self.cleaned_data["duration_hhmm"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


# ------------------------
# Visits
# ------------------------

class VisitRuleForm(forms.ModelForm):
    """
    Valide qu’on n’a pas déjà une visite avec le même nom pour le même aéronef.
    On reçoit l’aéronef via __init__(..., aircraft=...).
    Saisie HH:MM pour intervalle et échéance.
    """
    interval_hhmm = forms.CharField(
        label="Intervalle (HH:MM)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "100:00"}),
    )
    due_at_hhmm = forms.CharField(
        label="Échéance initiale (HH:MM)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "0:00"}),
    )

    class Meta:
        model = VisitRule
        fields = ["name", "interval_cycles", "due_at_cycles", "active"]
        widgets = {
            "interval_cycles": forms.NumberInput(attrs={"min": 0}),
            "due_at_cycles": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        self.aircraft = kwargs.pop("aircraft", None)
        super().__init__(*args, **kwargs)

        # Pré-remplissage HH:MM depuis minutes stockées
        if self.instance and self.instance.pk:
            self.fields["interval_hhmm"].initial = minutes_to_hhmm(self.instance.interval_minutes or 0)
            self.fields["due_at_hhmm"].initial = minutes_to_hhmm(self.instance.due_at_minutes or 0)
        else:
            self.fields["interval_hhmm"].initial = "0:00"
            self.fields["due_at_hhmm"].initial = "0:00"

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Le nom est obligatoire.")
        if not self.aircraft:
            return name

        qs = VisitRule.objects.filter(aircraft=self.aircraft, name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Une visite avec ce nom existe déjà pour cet aéronef.")
        return name

    def clean_interval_hhmm(self):
        val = (self.cleaned_data.get("interval_hhmm") or "").strip()
        minutes = hhmm_to_minutes(val) if val else 0
        if minutes <= 0:
            raise forms.ValidationError("L’intervalle doit être > 0.")
        return minutes

    def clean_due_at_hhmm(self):
        val = (self.cleaned_data.get("due_at_hhmm") or "").strip()
        return hhmm_to_minutes(val) if val else 0

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.interval_minutes = self.cleaned_data.get("interval_hhmm", 0)
        instance.due_at_minutes = self.cleaned_data.get("due_at_hhmm", 0)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class VisitCompleteForm(forms.Form):
    # on ne change pas tes noms existants pour éviter de casser fleet/views.py
    minutes_done_total = forms.CharField(
        label="Total cellule au moment de la réalisation (HH:MM)",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "1603:30"}),
    )
    cycles_done_total = forms.IntegerField(
        label="Cycles totaux au moment de la réalisation",
        min_value=0,
        required=False,
    )

    def clean_minutes_done_total(self):
        val = (self.cleaned_data.get("minutes_done_total") or "").strip()
        minutes = hhmm_to_minutes(val)
        if minutes < 0:
            raise forms.ValidationError("Valeur invalide.")
        return minutes
