from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Sum
from django.views.decorators.http import require_POST

from .models import Aircraft, FlightLog, VisitRule, VisitCompletion
from .forms import AircraftForm, FlightLogForm, VisitRuleForm, VisitCompleteForm

from kardex.alerting import component_level, aggregate_levels
from kardex.models import EngineLog


def _is_admin_or_super(user):
    return user.is_authenticated and user.role in {user.Roles.ADMIN, user.Roles.SUPERADMIN}


def _can_manage_visits(user):
    return user.is_authenticated and user.role in {user.Roles.ADMIN, user.Roles.SUPERADMIN, user.Roles.CAMO}


def _same_org_or_super(user, org_id):
    return user.is_authenticated and (user.role == user.Roles.SUPERADMIN or user.organization_id == org_id)


def _current_totals(aircraft: Aircraft):
    agg = aircraft.logs.aggregate(mins=Sum("duration_minutes"), cyc=Sum("cycles"))
    log_minutes = agg["mins"] or 0
    log_cycles = agg["cyc"] or 0
    total_minutes = aircraft.initial_minutes + log_minutes
    total_cycles = aircraft.initial_cycles + log_cycles
    return total_minutes, total_cycles


def _engine_current_totals(engine):
    agg = engine.logs.aggregate(mins=Sum("duration_minutes"), cyc=Sum("cycles"))
    log_minutes = agg["mins"] or 0
    log_cycles = agg["cyc"] or 0
    total_minutes = int(engine.initial_minutes or 0) + log_minutes
    total_cycles = int(engine.initial_cycles or 0) + log_cycles
    return total_minutes, total_cycles


def _fmt_hhmm(minutes: int) -> str:
    minutes = int(minutes or 0)
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"


@login_required
def aircraft_list(request):
    if request.user.role == request.user.Roles.SUPERADMIN:
        qs = Aircraft.objects.select_related("organization", "owner_user").prefetch_related(
            "installed_components", "engines", "engines__installed_components"
        ).all()
    else:
        qs = Aircraft.objects.select_related("organization", "owner_user").prefetch_related(
            "installed_components", "engines", "engines__installed_components"
        ).filter(organization=request.user.organization)

    for a in qs:
        levels = []
        for c in a.installed_components.all():
            levels.append(component_level(c))
        for e in a.engines.all():
            for c in e.installed_components.all():
                levels.append(component_level(c))
        a.kardex_level = aggregate_levels(levels)

    return render(request, "aircraft/list.html", {"aircraft": qs})


@login_required
def aircraft_create(request):
    if not _is_admin_or_super(request.user):
        return HttpResponseForbidden("Accès refusé : administrateur ou super administrateur uniquement.")

    if request.method == "POST":
        form = AircraftForm(request.POST, user=request.user)
        if form.is_valid():
            aircraft = form.save(commit=False)
            if request.user.role != request.user.Roles.SUPERADMIN:
                aircraft.organization = request.user.organization
            aircraft.save()
            messages.success(request, "Aéronef créé.")
            return redirect("aircraft_list")
    else:
        form = AircraftForm(user=request.user)

    return render(request, "aircraft/form.html", {"form": form, "mode": "create", "obj": None})


@login_required
def aircraft_edit(request, pk: int):
    obj = get_object_or_404(Aircraft, pk=pk)

    if not _is_admin_or_super(request.user):
        return HttpResponseForbidden("Accès refusé : administrateur ou super administrateur uniquement.")
    if request.user.role != request.user.Roles.SUPERADMIN and obj.organization_id != request.user.organization_id:
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = AircraftForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            aircraft = form.save(commit=False)
            if request.user.role != request.user.Roles.SUPERADMIN:
                aircraft.organization = request.user.organization
            aircraft.save()
            messages.success(request, "Aéronef modifié.")
            return redirect("aircraft_detail", pk=obj.pk)
    else:
        form = AircraftForm(instance=obj, user=request.user)

    return render(request, "aircraft/form.html", {"form": form, "mode": "edit", "obj": obj})


@login_required
def aircraft_detail(request, pk: int):
    obj = get_object_or_404(Aircraft, pk=pk)
    if request.user.role != request.user.Roles.SUPERADMIN and obj.organization_id != request.user.organization_id:
        return HttpResponseForbidden("Accès refusé.")

    total_minutes, total_cycles = _current_totals(obj)

    logs = []
    for row in obj.logs.select_related("pilot").all():
        logs.append({"row": row, "dur_hhmm": _fmt_hhmm(row.duration_minutes)})

    visits = []
    for r in obj.visit_rules.filter(active=True).order_by("name"):
        due = r.due_at_minutes or 0
        remain = due - total_minutes
        status = "ok" if remain > 0 else ("due" if remain == 0 else "overdue")
        visits.append({
            "rule": r,
            "remain_hhmm": _fmt_hhmm(remain),
            "remain_abs_hhmm": _fmt_hhmm(abs(remain)),
            "due_hhmm": _fmt_hhmm(due),
            "interval_hhmm": _fmt_hhmm(r.interval_minutes or 0),
            "status": status,
        })

    engines = obj.engines.prefetch_related("installed_components", "logs").all()
    airframe_components = obj.installed_components.all()

    comp_levels = {}
    levels_all = []

    for c in airframe_components:
        lvl = component_level(c)
        comp_levels[c.id] = lvl
        levels_all.append(lvl)

    for e in engines:
        for c in e.installed_components.all():
            lvl = component_level(c)
            comp_levels[c.id] = lvl
            levels_all.append(lvl)

    aircraft_kardex_level = aggregate_levels(levels_all)

    engines_ctx = []
    for e in engines:
        em, ec = _engine_current_totals(e)
        engines_ctx.append({
            "obj": e,
            "total_hhmm": _fmt_hhmm(em),
            "total_cycles": ec,
        })

    can_add_log = _same_org_or_super(request.user, obj.organization_id)
    can_manage_visits = _can_manage_visits(request.user) and _same_org_or_super(request.user, obj.organization_id)
    log_form = FlightLogForm() if can_add_log else None

    return render(
        request,
        "aircraft/detail.html",
        {
            "obj": obj,
            "logs": logs,
            "total_hhmm": _fmt_hhmm(total_minutes),
            "total_cycles": total_cycles,
            "base_hhmm": _fmt_hhmm(obj.initial_minutes),
            "log_hhmm": _fmt_hhmm(total_minutes - obj.initial_minutes),
            "log_cycles": (total_cycles - obj.initial_cycles),
            "can_add_log": can_add_log,
            "log_form": log_form,

            "visits": visits,
            "can_manage_visits": can_manage_visits,

            "airframe_components": airframe_components,
            "engines": engines_ctx,
            "comp_levels": comp_levels,
            "aircraft_kardex_level": aircraft_kardex_level,
        },
    )


@require_POST
@login_required
def flightlog_add(request, pk: int):
    obj = get_object_or_404(Aircraft, pk=pk)
    if not _same_org_or_super(request.user, obj.organization_id):
        return HttpResponseForbidden("Accès refusé.")

    form = FlightLogForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulaire invalide.")
        return redirect("aircraft_detail", pk=obj.pk)

    entry = form.save(commit=False)
    entry.aircraft = obj
    if not entry.pilot:
        entry.pilot = request.user
    entry.save()

    # === Auto : créer un log moteur par moteur (si moteurs déclarés) ===
    engines = obj.engines.all()
    if engines.exists():
        auto_remarks = []
        if entry.from_icao or entry.to_icao:
            auto_remarks.append(f"Vol {entry.from_icao or '—'} -> {entry.to_icao or '—'}")
        if entry.remarks:
            auto_remarks.append(entry.remarks.strip())
        remarks = " | ".join([x for x in auto_remarks if x]) or "Auto depuis journal de vol (cellule)"

        for e in engines:
            EngineLog.objects.create(
                engine=e,
                date=entry.date,
                duration_minutes=entry.duration_minutes,
                cycles=entry.cycles,
                remarks=remarks,
                created_by=request.user,
            )

        messages.success(request, "Ligne de journal ajoutée + logs moteurs créés automatiquement.")
    else:
        messages.success(request, "Ligne de journal ajoutée (aucun moteur déclaré).")

    return redirect("aircraft_detail", pk=obj.pk)


@login_required
def visitrule_create(request, aircraft_pk: int):
    aircraft = get_object_or_404(Aircraft, pk=aircraft_pk)
    if not (_can_manage_visits(request.user) and _same_org_or_super(request.user, aircraft.organization_id)):
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = VisitRuleForm(request.POST, aircraft=aircraft)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.aircraft = aircraft
            try:
                rule.save()
            except IntegrityError:
                form.add_error("name", "Une visite avec ce nom existe déjà pour cet aéronef.")
            else:
                messages.success(request, "Visite programmée créée.")
                return redirect("aircraft_detail", pk=aircraft.pk)
    else:
        form = VisitRuleForm(aircraft=aircraft)

    return render(request, "aircraft/visit_rule_form.html", {"form": form, "aircraft": aircraft, "mode": "create"})


@login_required
def visitrule_edit(request, rule_id: int):
    rule = get_object_or_404(VisitRule, pk=rule_id)
    aircraft = rule.aircraft
    if not (_can_manage_visits(request.user) and _same_org_or_super(request.user, aircraft.organization_id)):
        return HttpResponseForbidden("Accès refusé.")

    if request.method == "POST":
        form = VisitRuleForm(request.POST, instance=rule, aircraft=aircraft)
        if form.is_valid():
            form.save()
            messages.success(request, "Visite programmée mise à jour.")
            return redirect("aircraft_detail", pk=aircraft.pk)
    else:
        form = VisitRuleForm(instance=rule, aircraft=aircraft)

    return render(request, "aircraft/visit_rule_form.html", {"form": form, "aircraft": aircraft, "mode": "edit"})


@login_required
def visitrule_complete(request, rule_id: int):
    rule = get_object_or_404(VisitRule, pk=rule_id)
    aircraft = rule.aircraft
    if not (_can_manage_visits(request.user) and _same_org_or_super(request.user, aircraft.organization_id)):
        return HttpResponseForbidden("Accès refusé.")

    total_minutes_now, total_cycles_now = _current_totals(aircraft)
    due = rule.due_at_minutes or 0
    interval = rule.interval_minutes or 0
    overdue = max(0, total_minutes_now - due)
    next_due_preview = total_minutes_now + interval

    if request.method == "POST":
        form = VisitCompleteForm(request.POST)
        if form.is_valid():
            minutes_done_total = form.minutes_done_total
            cycles_done_total = form.cleaned_data.get("cycles_done_total") or total_cycles_now

            VisitCompletion.objects.create(
                rule=rule,
                date=timezone.localdate(),
                at_minutes=minutes_done_total,
                at_cycles=cycles_done_total,
                remarks=form.cleaned_data.get("remarks", ""),
            )

            rule.due_at_minutes = minutes_done_total + interval
            rule.due_at_cycles = cycles_done_total + (rule.interval_cycles or 0)
            rule.save(update_fields=["due_at_minutes", "due_at_cycles", "updated_at"])

            messages.success(request, "Visite enregistrée. Prochaine échéance mise à jour.")
            return redirect("aircraft_detail", pk=aircraft.pk)
    else:
        form = VisitCompleteForm(initial={"minutes_done_total": total_minutes_now, "cycles_done_total": total_cycles_now})

    ctx = {
        "form": form,
        "aircraft": aircraft,
        "rule": rule,
        "total_hhmm": _fmt_hhmm(total_minutes_now),
        "due_hhmm": _fmt_hhmm(due),
        "interval_hhmm": _fmt_hhmm(interval),
        "overdue_hhmm": _fmt_hhmm(overdue),
        "next_due_hhmm": _fmt_hhmm(next_due_preview),
    }
    return render(request, "aircraft/visit_complete_form.html", ctx)
