# consultasSQL/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.consultas_sql, name='consultas_sql'),  # Página principal de consultas SQL
    path('verTablas/', views.ver_tablas, name='ver_tablas'),  # Página para ver tablas
    path('verVistas/', views.ver_vistas, name='ver_vistas'),  # Página para ver vistas
    path('verTablas/<str:table_name>/', views.ver_resumen_tabla, name='ver_resumen_tabla'),  # Resumen de tabla
    path('verVistas/<str:view_name>/', views.ver_resumen_vista, name='ver_resumen_vista'),  # Resumen de vista
]
