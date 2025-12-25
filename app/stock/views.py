from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.db.models import Q

from .forms import StockItemForm
from .models import StockItem


def _org_id(user) -> int:
    return user.organization_id


def _has_admin_access(user) -> bool:
    # adapte si tu veux restreindre, mais au minimum ça évite les crash
    return user.is_authenticated


@login_required
def stock_home(request):
    return redirect("stock_item_list")


@login_required
def stock_item_list(request):
    org_id = _org_id(request.user)
    q = (request.GET.get("q") or "").strip()

    qs = StockItem.objects.filter(organization_id=org_id)

    if q:
        qs = qs.filter(
            Q(designation__icontains=q)
            | Q(pn__icontains=q)
            | Q(pn_mfr__icontains=q)
            | Q(ata__icontains=q)
            | Q(barcode__iexact=q)
        )

    items = qs.order_by("designation")[:200]

    return render(
        request,
        "stock/item_list.html",
        {"items": items, "q": q},
    )


@login_required
def item_create(request):
    org_id = _org_id(request.user)

    if request.method == "POST":
        form = StockItemForm(request.POST, org_id=org_id)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organization_id = org_id
            obj.save()
            form.save_m2m()  # locations

            messages.success(request, f"Article créé. Code barres: {obj.barcode}")
            return redirect("stock_item_list")
        messages.error(request, "Formulaire invalide.")
    else:
        form = StockItemForm(org_id=org_id)

    return render(request, "stock/item_form.html", {"form": form, "mode": "create"})
