from django.urls import path
from . import views

urlpatterns = [
    path("", views.stock_home, name="stock_home"),
    path("items/", views.stock_item_list, name="stock_item_list"),
    path("items/create/", views.item_create, name="stock_item_create"),
]

