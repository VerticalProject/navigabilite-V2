from django import template

register = template.Library()


@register.filter(name="hhmm")
def hhmm(value):
    """
    Convertit des minutes (int/str) en HH:MM.
    - None / "" -> "00:00"
    - valeurs négatives -> "-HH:MM"
    """
    if value in (None, ""):
        return "00:00"

    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return "00:00"

    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)

    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"
