# users/urls.py
from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # Índice: redirige según autenticación
    path("", views.index_view, name="index"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Home
    path("home/", views.home_view, name="home"),

    # Módulo Financiero (UI)
    path("finanzas/", views.modulo_financiero, name="modulo_financiero"),
    path("finanzas/carga-balance/", views.finanzas_carga_balance, name="finanzas_carga_balance"),
    path("finanzas/indicadores/", views.finanzas_form_indicadores, name="finanzas_form_indicadores"),
    path("finanzas/cupos/", views.finanzas_form_cupos, name="finanzas_form_cupos"),

    # API: árbol de archivos
    path("finanzas/api/tree/", views.finanzas_api_tree, name="finanzas_api_tree"),

    # API: subida de archivos
    path("finanzas/upload/", views.upload_libro_balance, name="finanzas_upload"),
]
