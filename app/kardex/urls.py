from django.urls import path
from . import views

urlpatterns = [
    # ✅ module “Parc composants”
    path("components/", views.component_list, name="component_list"),
    path("components/create/", views.component_create, name="component_create"),

    # détail existant
    path("components/<int:pk>/", views.component_detail, name="component_detail"),

    # moteur (si tu le gardes, même si on n’utilise plus le formulaire)
    path("engines/<int:engine_id>/log/add/", views.engine_log_add, name="engine_log_add"),
]
