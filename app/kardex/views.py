from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Component, KardexEntry, Engine
from .forms import KardexEntryForm, EngineLogForm, ComponentForm
from .alerting import compute_component_usage, compute_alert_level


WARN_MINUTES = 10 * 60
WARN_CYCLES = 50


def _can_manage_kardex(user):
    return user.is_authenticated and user.role in {
        user.Roles.ADMIN,
        user.Roles.SUPERADMIN,
        user.Roles.CAMO,
    }


def _component_org_id(component: Component):
    if component.installed_engine:
        return component.installed_engine.aircraft.organization_id
    if component.installed_aircraft:
        return component.installed_aircraft.organization_id

    last = (
        component.entries.select_related("aircraft", "engine", "engine__aircraft")
        .exclude(aircraft__isnull=True, engine__isnull=True)
        .order_by("-date", "-id")
        .first()
    )
    if not last:
        return None
    if last.engine:
        return last.engine.aircraft.organization_id
    if last.aircraft:
        return last.aircraft.organization_id
    return None


def _can_view_component(user, component: Component) -> bool:
    if not user.is_authenticated:
        return False
    if user.role == user.Roles.SUPERADMIN:
        return True

    org_id = _component_org_id(component)
    if org_id is None:
        # composant jamais “vu” nulle part : on autorise si user a une org
        return user.organization_id is not None
    return user.organization_id == org_id


def _components_queryset_for_user(user):
    qs = Component.objects.select_related("installed_aircraft", "installed_engine", "installed_engine__aircraft").all()
    if user.role == user.Roles.SUPERADMIN:
        return qs

    # Si le composant est installé : on filtre par org de la machine
    qs_installed = qs.filter(
        Q(installed_aircraft__organization_id=user.organization_id) |
        Q(installed_engine__aircraft__organization_id=user.organization_id)
    )

    # Si pas installé : on prend ceux qui ont au moins un event kardex dans l'org
    qs_not_installed = qs.filter(
        installed_aircraft__isnull=True,
        installed_engine__isnull=True,
    ).filter(
        Q(entries__aircraft__organization_id=user.organization_id) |
        Q(entries__engine__aircraft__organization_id=user.organization_id)
    )

    return (qs_installed | qs_not_installed).distinct()


@login_required
def component_list(request):
    qs = _components_queryset_for_user(request.user)

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    ata = (request.GET.get("ata") or "").strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(part_number__icontains=q) |
            Q(serial_number__icontains=q) |
            Q(manufacturer__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if ata:
        # Filtre “simple” : ATA exact ou commence par (ex: "32" match "32-xx")
        qs = qs.filter(Q(ata__iexact=ata) | Q(ata__istartswith=ata))

    qs = qs.order_by("name", "part_number", "serial_number")

    ata_values = (
        _components_queryset_for_user(request.user)
        .exclude(ata__exact="")
        .values_list("ata", flat=True)
        .distinct()
        .order_by("ata")
    )

    ctx = {
        "components": qs,
        "q": q,
        "status": status,
        "ata": ata,
        "status_choices": Component.Status.choices,
        "ata_values": list(ata_values),
        "can_manage": _can_manage_kardex(request.user),
    }
    return render(request, "kardex/component_list.html", ctx)


@login_required
def component_create(request):
    if not _can_manage_kardex(request.user):
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = ComponentForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Composant créé.")
            return redirect("component_detail", pk=obj.pk)
        messages.error(request, "Formulaire invalide.")
    else:
        form = ComponentForm()

    return render(request, "kardex/component_form.html", {"form": form})


@login_required
def component_detail(request, pk: int):
    comp = get_object_or_404(Component, pk=pk)

    if not _can_view_component(request.user, comp):
        return HttpResponseForbidden("Accès refusé.")

    can_manage = _can_manage_kardex(request.user)

    entries = comp.entries.select_related(
        "aircraft",
        "engine",
        "engine__aircraft",
        "created_by",
    ).all()

    if request.method == "POST":
        if not can_manage:
            return HttpResponseForbidden("Accès refusé.")

        form = KardexEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.component = comp
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Évènement kardex ajouté.")
            return redirect("component_detail", pk=comp.pk)
        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = KardexEntryForm(initial={"date": timezone.localdate()}) if can_manage else None

    tsn_minutes, csn_cycles = compute_component_usage(comp)
    level = compute_alert_level(comp, tsn_minutes, csn_cycles)

    rem_minutes = None
    rem_cycles = None
    if comp.limit_minutes and comp.limit_minutes > 0:
        rem_minutes = int(comp.limit_minutes) - int(tsn_minutes)
    if comp.limit_cycles and comp.limit_cycles > 0:
        rem_cycles = int(comp.limit_cycles) - int(csn_cycles)

    alert = {
        "level": level,
        "rem_minutes": rem_minutes,
        "rem_cycles": rem_cycles,
    }

    return render(
        request,
        "kardex/component_detail.html",
        {
            "comp": comp,
            "entries": entries,
            "can_manage": can_manage,
            "form": form,
            "tsn_minutes": tsn_minutes,
            "csn_cycles": csn_cycles,
            "alert": alert,
        },
    )


@require_POST
@login_required
def engine_log_add(request, engine_id: int):
    engine = get_object_or_404(Engine, pk=engine_id)

    if request.user.role != request.user.Roles.SUPERADMIN and request.user.organization_id != engine.aircraft.organization_id:
        return HttpResponseForbidden("Accès refusé.")

    form = EngineLogForm(request.POST)
    if form.is_valid():
        row = form.save(commit=False)
        row.engine = engine
        row.created_by = request.user
        row.save()
        messages.success(request, "Ligne moteur ajoutée.")
    else:
        messages.error(request, "Formulaire moteur invalide.")

    return redirect("aircraft_detail", pk=engine.aircraft_id)
