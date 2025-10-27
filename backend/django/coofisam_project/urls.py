"""
Coofisam360 - Configuración de URLs Principal

Configuración central de rutas del sistema Coofisam360.
Define todas las URLs disponibles para las aplicaciones del proyecto.

Autor: Equipo de Desarrollo Coofisam360
Versión: 1.0
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

# =============================================================================
# VISTAS DE FALLBACK
# =============================================================================

# Vistas de respaldo en caso de error en la importación de vistas del proyecto
try:
    from coofisam_project.views import home_view, api_info
except Exception:
    from django.http import HttpResponse, JsonResponse
    
    def home_view(request):
        """Vista de respaldo para la página principal"""
        return HttpResponse("<title>Coofisam360 - Sistema Integral</title>OK")
    
    def api_info(request):
        """Vista de respaldo para información de la API"""
        return JsonResponse({"service": "coofisam360", "status": "ok"})

# =============================================================================
# CONFIGURACIÓN DE URLS
# =============================================================================

urlpatterns = [
    # Página principal y endpoint informativo
    path('', home_view, name='home'),                    # Página principal del sistema
    path('info/', api_info, name='api-info'),           # Información de la API

    # Panel de administración de Django
    path('admin/', admin.site.urls),                    # Administración del sistema

    # URLs de aplicaciones web del proyecto
    path('users/', include('users.urls')),              # Gestión de usuarios
    path('consultas/', include('consultasSQL.urls')),   # Módulo de consultas SQL

    # URLs de la API REST
    path('api/v1/', include('users.api_urls')),         # API de usuarios
    path('api/v1/talento/', include('talento_cultura.api_urls')), # API de talento y cultura

    # API de autenticación de Django REST Framework
    path('api-auth/', include('rest_framework.urls')),  # Autenticación API

    # Redirección de login al panel de administración
    path('login/', RedirectView.as_view(url='/admin/login/', permanent=False), name='login-redirect'),
]
