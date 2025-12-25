from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Organization

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "avatar"]
        widgets = {
            "email": forms.EmailInput(),
        }


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "organization",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        # Organisation : superadmin peut choisir n'importe quoi
        if self.request_user and getattr(self.request_user, "role", None) != self.request_user.Roles.SUPERADMIN:
            self.fields["organization"].queryset = Organization.objects.filter(id=self.request_user.organization_id)
            self.fields["organization"].initial = self.request_user.organization_id

        # UX : champs optionnels + placeholders
        self.fields["email"].required = False
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False

        self.fields["username"].widget.attrs.update({"placeholder": "ex: jdupont"})
        self.fields["email"].widget.attrs.update({"placeholder": "ex: jean.dupont@email.com"})

    def clean_organization(self):
        org = self.cleaned_data.get("organization")

        # Si admin (pas superadmin) => force org de l'admin
        if self.request_user and self.request_user.role != self.request_user.Roles.SUPERADMIN:
            return self.request_user.organization

        return org

    def clean_role(self):
        role = self.cleaned_data.get("role")

        # Empêche un admin de créer un superadmin
        if self.request_user and self.request_user.role != self.request_user.Roles.SUPERADMIN:
            if role == self.request_user.Roles.SUPERADMIN:
                raise forms.ValidationError("Seul un super administrateur peut créer un super administrateur.")

        return role


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "organization",
        ]
        widgets = {
            "email": forms.EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        # Organisation : superadmin peut choisir n'importe quoi
        if self.request_user and getattr(self.request_user, "role", None) != self.request_user.Roles.SUPERADMIN:
            self.fields["organization"].queryset = Organization.objects.filter(id=self.request_user.organization_id)
            self.fields["organization"].initial = self.request_user.organization_id

        # UX
        self.fields["email"].required = False
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False

        self.fields["username"].widget.attrs.update({"placeholder": "ex: jdupont"})
        self.fields["email"].widget.attrs.update({"placeholder": "ex: jean.dupont@email.com"})

    def clean_organization(self):
        org = self.cleaned_data.get("organization")

        # Si admin (pas superadmin) => force org de l'admin
        if self.request_user and self.request_user.role != self.request_user.Roles.SUPERADMIN:
            return self.request_user.organization

        return org

    def clean_role(self):
        role = self.cleaned_data.get("role")

        # Empêche un admin de promouvoir en superadmin
        if self.request_user and self.request_user.role != self.request_user.Roles.SUPERADMIN:
            if role == self.request_user.Roles.SUPERADMIN:
                raise forms.ValidationError("Seul un super administrateur peut créer un super administrateur.")

        return role
