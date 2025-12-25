from django import forms
from .models import KardexEntry, EngineLog, Component


def _parse_hhmm_to_minutes_allow_zero(value: str) -> int:
    raw = (value or "").strip()
    if raw == "":
        return 0
    parts = raw.split(":")
    if len(parts) != 2:
        raise forms.ValidationError("Format invalide. Utilise HH:MM (ex: 01:30).")
    h_str, m_str = parts[0].strip(), parts[1].strip()
    if not (h_str.isdigit() and m_str.isdigit()):
        raise forms.ValidationError("Format invalide. Utilise HH:MM (ex: 01:30).")
    h = int(h_str)
    m = int(m_str)
    if h < 0:
        raise forms.ValidationError("Les heures doivent être positives.")
    if m < 0 or m > 59:
        raise forms.ValidationError("Les minutes doivent être entre 00 et 59.")
    return h * 60 + m


def _parse_hhmm_to_minutes(value: str) -> int:
    minutes = _parse_hhmm_to_minutes_allow_zero(value)
    if minutes <= 0:
        raise forms.ValidationError("La durée doit être > 00:00.")
    return minutes


class KardexEntryForm(forms.ModelForm):
    at_hhmm = forms.CharField(
        label="Total au moment de l’action (HH:MM)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "0123:45"}),
        help_text="Total machine (cellule ou moteur) au moment de l’action. Vide = 00:00.",
    )

    class Meta:
        model = KardexEntry
        fields = [
            "action",
            "date",
            "aircraft",
            "engine",
            "position",
            "at_cycles",
            "workorder_ref",
            "remarks",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "at_cycles": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_at_hhmm(self):
        return _parse_hhmm_to_minutes_allow_zero(self.cleaned_data.get("at_hhmm"))

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        aircraft = cleaned.get("aircraft")
        engine = cleaned.get("engine")

        if aircraft and engine:
            raise forms.ValidationError("Choisis soit Aircraft, soit Engine (pas les deux).")

        if action in {KardexEntry.Action.INSTALL, KardexEntry.Action.REMOVE}:
            if not aircraft and not engine:
                raise forms.ValidationError("Pour INSTALL/REMOVE, il faut cibler un Aircraft ou un Engine.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.at_minutes = self.cleaned_data.get("at_hhmm") or 0
        if commit:
            obj.save()
        return obj


class EngineLogForm(forms.ModelForm):
    duration_hhmm = forms.CharField(
        label="Durée (HH:MM)",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "01:30"}),
    )

    class Meta:
        model = EngineLog
        fields = ["date", "cycles", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "cycles": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_duration_hhmm(self):
        return _parse_hhmm_to_minutes(self.cleaned_data.get("duration_hhmm"))

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.duration_minutes = self.cleaned_data["duration_hhmm"]
        if commit:
            obj.save()
        return obj


# ✅ Nouveau : création composant
class ComponentForm(forms.ModelForm):
    class Meta:
        model = Component
        fields = [
            "category",
            "ata",
            "name",
            "manufacturer",
            "part_number",
            "serial_number",
            "initial_tsn_minutes",
            "initial_csn_cycles",
            "limit_minutes",
            "limit_cycles",
            "status",
        ]
        widgets = {
            "ata": forms.TextInput(attrs={"placeholder": "24"}),
            "initial_tsn_minutes": forms.NumberInput(attrs={"min": 0}),
            "initial_csn_cycles": forms.NumberInput(attrs={"min": 0}),
            "limit_minutes": forms.NumberInput(attrs={"min": 0}),
            "limit_cycles": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_ata(self):
        ata = (self.cleaned_data.get("ata") or "").strip()
        # On tolère vide. Sinon on normalise un peu.
        return ata
