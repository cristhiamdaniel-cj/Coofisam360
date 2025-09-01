# coofisam_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Incluye con namespace 'users'
    path('', include(('users.urls', 'users'), namespace='users')),

    path('consultasSQL/', include('consultasSQL.urls')),
]
