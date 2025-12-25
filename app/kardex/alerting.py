from django.db.models import Sum
from fleet.models import Aircraft
from .models import Component, KardexEntry, Engine, EngineLog

WARN_MINUTES = 10 * 60
WARN_CYCLES = 50


def aircraft_current_totals(aircraft: Aircraft):
    agg = aircraft.logs.aggregate(mins=Sum("duration_minutes"), cyc=Sum("cycles"))
    log_minutes = agg["mins"] or 0
    log_cycles = agg["cyc"] or 0
    total_minutes = aircraft.initial_minutes + log_minutes
    total_cycles = aircraft.initial_cycles + log_cycles
    return total_minutes, total_cycles


def engine_current_totals(engine: Engine):
    agg = engine.logs.aggregate(mins=Sum("duration_minutes"), cyc=Sum("cycles"))
    log_minutes = agg["mins"] or 0
    log_cycles = agg["cyc"] or 0
    total_minutes = int(engine.initial_minutes or 0) + log_minutes
    total_cycles = int(engine.initial_cycles or 0) + log_cycles
    return total_minutes, total_cycles


def compute_component_usage(comp: Component):
    entries = comp.entries.select_related("aircraft", "engine", "engine__aircraft").order_by("date", "id")

    used_minutes = 0
    used_cycles = 0

    installed = False
    start_minutes = None
    start_cycles = None
    start_target_aircraft = None
    start_target_engine = None

    def close_period(end_minutes, end_cycles):
        nonlocal used_minutes, used_cycles, installed, start_minutes, start_cycles, start_target_aircraft, start_target_engine
        if start_minutes is None:
            return
        if end_minutes is not None and end_minutes > 0:
            used_minutes += max(0, int(end_minutes) - int(start_minutes))
        if end_cycles is not None and end_cycles > 0 and start_cycles is not None:
            used_cycles += max(0, int(end_cycles) - int(start_cycles))
        installed = False
        start_minutes = None
        start_cycles = None
        start_target_aircraft = None
        start_target_engine = None

    for e in entries:
        if e.action == KardexEntry.Action.INSTALL:
            installed = True
            start_minutes = int(e.at_minutes or 0) if (e.at_minutes or 0) > 0 else None
            start_cycles = int(e.at_cycles or 0) if (e.at_cycles or 0) > 0 else None
            start_target_aircraft = e.aircraft
            start_target_engine = e.engine

        elif e.action in {KardexEntry.Action.REMOVE, KardexEntry.Action.SEND_SHOP, KardexEntry.Action.SCRAP}:
            if installed:
                close_period(e.at_minutes, e.at_cycles)

    if installed:
        end_minutes = None
        end_cycles = None
        if start_target_aircraft:
            end_minutes, end_cycles = aircraft_current_totals(start_target_aircraft)
        elif start_target_engine:
            end_minutes, end_cycles = engine_current_totals(start_target_engine)
        close_period(end_minutes, end_cycles)

    tsn_minutes = int(comp.initial_tsn_minutes or 0) + used_minutes
    csn_cycles = int(comp.initial_csn_cycles or 0) + used_cycles
    return tsn_minutes, csn_cycles


def compute_alert_level(comp: Component, tsn_minutes: int, csn_cycles: int):
    has_limits = False
    level = "ok"

    if comp.limit_minutes and comp.limit_minutes > 0:
        has_limits = True
        rem = int(comp.limit_minutes) - int(tsn_minutes)
        if rem < 0:
            return "overdue"
        if rem <= WARN_MINUTES:
            level = "warn"

    if comp.limit_cycles and comp.limit_cycles > 0:
        has_limits = True
        rem = int(comp.limit_cycles) - int(csn_cycles)
        if rem < 0:
            return "overdue"
        if rem <= WARN_CYCLES:
            level = "warn"

    if not has_limits:
        return "na"

    return level


def component_level(comp: Component):
    tsn, csn = compute_component_usage(comp)
    return compute_alert_level(comp, tsn, csn)


def aggregate_levels(levels):
    levels = [l for l in levels if l]
    if not levels:
        return "na"
    if "overdue" in levels:
        return "overdue"
    if "warn" in levels:
        return "warn"
    if "ok" in levels:
        return "ok"
    return "na"
