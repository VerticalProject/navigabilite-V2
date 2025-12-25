from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path("", views.home_redirect, name="home"),

    # Profil / paramètres
    path("profile/", views.profile_view, name="profile"),  # redirige vers settings
    path("settings/", views.settings_view, name="settings"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),

    # Mot de passe
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="users/password_change.html"
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="users/password_change_done.html"
        ),
        name="password_change_done",
    ),

    # -------------------------
    # Administration
    # -------------------------
    path("administration/", views.admin_home, name="admin_home"),

    # Organisations
    path("organizations/", views.org_list, name="org_list"),
    path("organizations/create/", views.org_create, name="org_create"),
    path("organizations/<int:pk>/edit/", views.org_edit, name="org_edit"),

    # Utilisateurs
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
]
