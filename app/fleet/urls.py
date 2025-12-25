from django.urls import path
from . import views

urlpatterns = [
    path("", views.aircraft_list, name="aircraft_list"),
    path("create/", views.aircraft_create, name="aircraft_create"),
    path("<int:pk>/", views.aircraft_detail, name="aircraft_detail"),
    path("<int:pk>/edit/", views.aircraft_edit, name="aircraft_edit"),

    # Journal de vol
    path("<int:pk>/log/add/", views.flightlog_add, name="flightlog_add"),

    # Visites (règles + complétion)
    path("<int:aircraft_pk>/visits/create/", views.visitrule_create, name="visitrule_create"),
    path("visits/<int:rule_id>/edit/", views.visitrule_edit, name="visitrule_edit"),
    path("visits/<int:rule_id>/complete/", views.visitrule_complete, name="visitrule_complete"),
]