from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs de aplicaciones web existentes
    path('users/', include('users.urls')),
    path('consultas/', include('consultasSQL.urls')),
    
    # URLs de la API REST
    path('api/v1/', include('users.api_urls')),
    
    # API de autenticación de Django REST Framework
    path('api-auth/', include('rest_framework.urls')),
]
