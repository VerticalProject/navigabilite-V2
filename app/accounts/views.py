from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileUpdateForm, UserCreateForm, UserUpdateForm
from .models import Organization  # <-- important : Organization est dans accounts.models

User = get_user_model()


# -------------------------
# Permissions
# -------------------------
def _has_admin_access(user) -> bool:
    if not user.is_authenticated:
        return False

    # Admin Django (createsuperuser) ou staff => OK
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    # Admin "app" via champ role (string ou enum)
    role = getattr(user, "role", None)

    # cas string
    if role in {"admin", "superadmin", "ADMIN", "SUPERADMIN"}:
        return True

    # cas enum (User.Roles.ADMIN / SUPERADMIN)
    Roles = getattr(user, "Roles", None)
    if Roles:
        try:
            return role in {Roles.ADMIN, Roles.SUPERADMIN}
        except Exception:
            pass

    return False


def _can_manage_users(user) -> bool:
    return _has_admin_access(user)


def _can_manage_orgs(user) -> bool:
    return _has_admin_access(user)


def _detect_user_type_attr() -> str:
    """
    Filtre "type" activé uniquement si le champ existe vraiment (user_type ou type).
    """
    try:
        User._meta.get_field("user_type")
        return "user_type"
    except Exception:
        pass
    try:
        User._meta.get_field("type")
        return "type"
    except Exception:
        return ""


def _type_choices_and_attr():
    attr = _detect_user_type_attr()
    if not attr:
        return [], ""
    if attr == "user_type" and hasattr(User, "UserTypes"):
        return list(User.UserTypes.choices), "user_type"
    if attr == "type" and hasattr(User, "Types"):
        return list(User.Types.choices), "type"
    return [], attr


# -------------------------
# Administration
# -------------------------
@login_required
def admin_home(request):
    if not _has_admin_access(request.user):
        return HttpResponseForbidden("Accès refusé.")

    tiles = []

    if _can_manage_users(request.user):
        tiles.append(
            {
                "title": "Utilisateurs",
                "subtitle": "Créer, modifier, gérer les comptes",
                "url": "user_list",
                "enabled": True,
            }
        )

    if _can_manage_orgs(request.user):
        tiles.append(
            {
                "title": "Organisations",
                "subtitle": "Gérer les organisations et infos",
                "url": "org_list",
                "enabled": True,
            }
        )

    return render(request, "admin/home.html", {"tiles": tiles, "can_manage": True})

# -------------------------
# Home / Profile / Settings
# -------------------------
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("profile")
    return redirect("login")


@login_required
def profile_view(request):
    # /profile/ -> settings (comme dans ton urls.py commenté)
    return redirect("settings")


@login_required
def settings_view(request):
    return render(request, "settings.html", {})


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("profile")
        messages.error(request, "Formulaire invalide.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "users/profile_edit.html", {"form": form})


# -------------------------
# Organizations (safe form)
# -------------------------
def _org_fields():
    # ton Organization n'a visiblement que "name" (on garde ça safe)
    # si plus tard tu ajoutes d'autres champs, tu peux les rajouter ici.
    return ["name"]


def _build_org_form(data=None, instance=None):
    fields = _org_fields()

    class OrgForm(forms.ModelForm):
        class Meta:
            model = Organization
            fields = fields

    return OrgForm(data=data, instance=instance)


@login_required
def org_list(request):
    orgs = Organization.objects.order_by("name")
    return render(request, "organizations/list.html", {"orgs": orgs})


@login_required
def org_create(request):
    if not _can_manage_orgs(request.user):
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = _build_org_form(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Organisation créée.")
            return redirect("org_list")
        messages.error(request, "Formulaire invalide.")
    else:
        form = _build_org_form()

    return render(request, "organizations/form.html", {"form": form, "mode": "create"})


@login_required
def org_edit(request, pk: int):
    if not _can_manage_orgs(request.user):
        return HttpResponseForbidden("Accès refusé.")

    obj = get_object_or_404(Organization, pk=pk)

    if request.method == "POST":
        form = _build_org_form(data=request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Organisation mise à jour.")
            return redirect("org_list")
        messages.error(request, "Formulaire invalide.")
    else:
        form = _build_org_form(instance=obj)

    return render(request, "organizations/form.html", {"form": form, "mode": "edit"})


# -------------------------
# Users
# -------------------------
@login_required
def user_list(request):
    qs = User.objects.select_related("organization").all()

    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()
    org = (request.GET.get("org") or "").strip()
    typ = (request.GET.get("type") or "").strip()

    # Admin (non superadmin) => ne voit que son org
    if request.user.role != request.user.Roles.SUPERADMIN:
        qs = qs.filter(organization_id=request.user.organization_id)

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )

    if role:
        qs = qs.filter(role=role)

    if org:
        qs = qs.filter(organization_id=org)

    type_choices, type_attr = _type_choices_and_attr()
    if typ and type_attr:
        qs = qs.filter(**{type_attr: typ})

    qs = qs.order_by("last_name", "first_name", "username")

    orgs_qs = Organization.objects.order_by("name")
    if request.user.role != request.user.Roles.SUPERADMIN:
        orgs_qs = orgs_qs.filter(id=request.user.organization_id)

    ctx = {
        "users": qs,
        "q": q,
        "role": role,
        "org": org,
        "type": typ,
        "role_choices": list(User.Roles.choices) if hasattr(User, "Roles") else [],
        "type_choices": type_choices,
        "user_type_attr": type_attr,
        "orgs": orgs_qs,
        "can_manage": _can_manage_users(request.user),
    }
    return render(request, "users/list.html", ctx)


@login_required
def user_create(request):
    if not _can_manage_users(request.user):
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = UserCreateForm(request.POST, request_user=request.user)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Utilisateur créé.")
            return redirect("user_edit", pk=obj.pk)
        messages.error(request, "Formulaire invalide.")
    else:
        form = UserCreateForm(request_user=request.user)

    return render(request, "users/form.html", {"form": form, "mode": "create", "obj": None})


@login_required
def user_edit(request, pk: int):
    if not _can_manage_users(request.user):
        return HttpResponseForbidden("Accès refusé.")

    obj = get_object_or_404(User.objects.select_related("organization"), pk=pk)

    # Admin (non superadmin) => interdit de modifier un user hors org
    if request.user.role != request.user.Roles.SUPERADMIN and obj.organization_id != request.user.organization_id:
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=obj, request_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur mis à jour.")
            return redirect("user_edit", pk=obj.pk)
        messages.error(request, "Formulaire invalide.")
    else:
        form = UserUpdateForm(instance=obj, request_user=request.user)

    return render(request, "users/form.html", {"form": form, "mode": "edit", "obj": obj})
