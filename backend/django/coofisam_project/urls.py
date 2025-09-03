from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

# Fallback seguro si no se pueden importar las vistas del proyecto
try:
    from coofisam_project.views import home_view, api_info  # ajusta si tus vistas están en otro módulo
except Exception:
    from django.http import HttpResponse, JsonResponse
    def home_view(request):
        return HttpResponse("<title>Coofisam360 - Sistema Integral</title>OK")
    def api_info(request):
        return JsonResponse({"service": "coofisam360", "status": "ok"})

urlpatterns = [
    # Página principal y endpoint informativo
    path('', home_view, name='home'),
    path('info/', api_info, name='api-info'),

    # Administración
    path('admin/', admin.site.urls),

    # URLs de aplicaciones web existentes
    path('users/', include('users.urls')),
    path('consultas/', include('consultasSQL.urls')),

    # URLs de la API REST
    path('api/v1/', include('users.api_urls')),

    # API de autenticación de DRF
    path('api-auth/', include('rest_framework.urls')),

    # Redirección de /login/ → /admin/login/
    path('login/', RedirectView.as_view(url='/admin/login/', permanent=False), name='login-redirect'),
]
