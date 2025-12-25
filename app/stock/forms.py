from django import forms
from .models import StockItem, StockLocation


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = ["designation", "pn", "pn_mfr", "ata", "locations", "is_active"]
        widgets = {
            "locations": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        org_id = kwargs.pop("org_id", None)
        super().__init__(*args, **kwargs)

        if org_id:
            self.fields["locations"].queryset = StockLocation.objects.filter(
                organization_id=org_id
            ).order_by("name")
        else:
            self.fields["locations"].queryset = StockLocation.objects.none()

    def clean_designation(self):
        v = (self.cleaned_data.get("designation") or "").strip()
        if not v:
            raise forms.ValidationError("Désignation obligatoire.")
        return v
