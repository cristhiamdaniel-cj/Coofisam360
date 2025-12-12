"""
Coofisam360 - Configuración del Proyecto Django

Sistema integral de gestión para cooperativas financieras.
Configuración principal del proyecto Django con todas las aplicaciones
y configuraciones necesarias para el funcionamiento del sistema.

Autor: Equipo de Desarrollo Coofisam360
Versión: 1.0
Última actualización: 2025
"""

from pathlib import Path
import os

# Configuración de rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de archivos multimedia
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Configuración específica para archivos Excel del Libro de Balance
# Ruta unificada con el sistema ETL existente
from pathlib import Path as _P
LIBRO_BALANCE_ROOT = _P('/home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo')
LIBRO_BALANCE_ROOT.mkdir(parents=True, exist_ok=True)

# Permisos de archivos subidos (lectura para todos, escritura solo para propietario)
FILE_UPLOAD_PERMISSIONS = 0o644

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD Y ENTORNO
# =============================================================================

# Clave secreta para firmas criptográficas (CAMBIAR EN PRODUCCIÓN)
# IMPORTANTE: Esta clave debe ser única y mantenerse en secreto
SECRET_KEY = 'django-insecure-#j0h06r!vq-7^uha=p-v7gz91o0(u)0s$qm!$xy^o93(9e@7dp'

"""Ajustes sensibles por entorno"""
# Modo de depuración (usar DJANGO_DEBUG si está definido)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

# Hosts permitidos para el servidor Django
# Configuración para desarrollo local y túneles ngrok
# Hosts permitidos (se puede sobreescribir con DJANGO_ALLOWED_HOSTS="host1,host2")
_hosts = os.getenv("DJANGO_ALLOWED_HOSTS")
if _hosts:
    ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = [
        "localhost", "127.0.0.1", "0.0.0.0", "coofisam360.ngrok.io", "inti-data.ngrok.io"
    ]



# =============================================================================
# CONFIGURACIÓN DE APLICACIONES DJANGO
# =============================================================================

# Aplicaciones instaladas en el proyecto
INSTALLED_APPS = [
    # Aplicaciones core de Django
    'django.contrib.admin',        # Panel de administración
    'django.contrib.auth',         # Sistema de autenticación
    'django.contrib.contenttypes', # Framework de tipos de contenido
    'django.contrib.sessions',     # Manejo de sesiones
    'django.contrib.messages',     # Sistema de mensajes
    'django.contrib.staticfiles',  # Manejo de archivos estáticos
    
    # Aplicaciones de terceros
    'rest_framework',              # Django REST Framework
    'rest_framework.authtoken',    # Autenticación por token
    'corsheaders',                 # Manejo de CORS
    
    # Aplicaciones del proyecto
    'users',                       # Gestión de usuarios y perfiles
    'consultasSQL',               # Módulo de consultas SQL
    'talento_cultura',            # Módulo de talento y cultura
]
# =============================================================================
# CONFIGURACIÓN DE MIDDLEWARE
# =============================================================================

# Middleware procesado en orden secuencial
# IMPORTANTE: El orden de los middleware es crítico para el funcionamiento
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # Seguridad general
    'corsheaders.middleware.CorsMiddleware',              # Manejo de CORS
    'django.contrib.sessions.middleware.SessionMiddleware', # Gestión de sesiones
    'django.middleware.common.CommonMiddleware',          # Funcionalidad común
    'django.middleware.csrf.CsrfViewMiddleware',          # Protección CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Autenticación
    'django.contrib.messages.middleware.MessageMiddleware', # Sistema de mensajes
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Protección clickjacking
    'whitenoise.middleware.WhiteNoiseMiddleware',         # Servir archivos estáticos
]
# Configuración de URLs principal
ROOT_URLCONF = 'coofisam_project.urls'

# =============================================================================
# CONFIGURACIÓN DE PLANTILLAS
# =============================================================================

# Configuración del motor de plantillas Django
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Directorios adicionales de plantillas
        'APP_DIRS': True,  # Buscar plantillas en directorios de aplicaciones
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',      # Objeto request
                'django.contrib.auth.context_processors.auth',     # Usuario autenticado
                'django.contrib.messages.context_processors.messages', # Mensajes del sistema
            ],
        },
    },
]

# Aplicación WSGI para despliegue
WSGI_APPLICATION = 'coofisam_project.wsgi.application'


# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================

# Configuración de conexión a PostgreSQL
# Base de datos principal del sistema Coofisam360
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'coofisam_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Alejito10.'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        # 'OPTIONS': { 'options': '-c search_path=finanzas,public' },
    }
}



# =============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# =============================================================================

# Validadores de contraseñas para seguridad
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =============================================================================
# CONFIGURACIÓN DE INTERNACIONALIZACIÓN
# =============================================================================

# Configuración de idioma y zona horaria
LANGUAGE_CODE = 'en-us'              # Idioma por defecto
TIME_ZONE = 'America/Bogota'         # Zona horaria de Colombia
USE_TZ = True                        # Usar zona horaria
USE_I18N = True                      # Habilitar internacionalización




# =============================================================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# =============================================================================

# Configuración para archivos CSS, JavaScript e imágenes
STATIC_URL = '/static/'                                    # URL base para archivos estáticos
STATIC_ROOT = BASE_DIR / 'staticfiles'                    # Directorio para collectstatic
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]     # Directorios adicionales de archivos estáticos

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

# Tipo de campo primario por defecto para modelos
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# URL de redirección después del login
LOGIN_REDIRECT_URL = 'users:home'

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD CSRF
# =============================================================================

# Orígenes confiables para CSRF (túneles ngrok y desarrollo local)
CSRF_TRUSTED_ORIGINS = [
    'https://coofisam360.ngrok.io', 
    'https://coofisam360.ngrok.io',
]

# =============================================================================
# CONFIGURACIÓN DE DJANGO REST FRAMEWORK
# =============================================================================

# Configuración de la API REST
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # Autenticación por sesión
        'rest_framework.authentication.TokenAuthentication',    # Autenticación por token
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',           # Requiere autenticación
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20  # Tamaño de página por defecto
}

# =============================================================================
# CONFIGURACIÓN DE CORS (Cross-Origin Resource Sharing)
# =============================================================================

# Orígenes permitidos para peticiones CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",         # Desarrollo local frontend
    "http://127.0.0.1:3000",        # Loopback local
    "http://localhost:8061",         # Frontend local puerto 8061
    "https://coofisam360.ngrok.io", # Túnel ngrok backend
    "https://coofisam360-backend.ngrok.io", # Túnel ngrok backend específico
    "https://coofisam360-frontend.ngrok.io", # Túnel ngrok frontend
]

# Orígenes confiables para CSRF (duplicado para claridad)
CSRF_TRUSTED_ORIGINS = [
    "https://coofisam360.ngrok.io",
    "https://coofisam360-backend.ngrok.io",
    "https://coofisam360-frontend.ngrok.io",
    "https://inti-data.ngrok.io",
    "http://localhost:3000",
    "http://localhost:8061",
    "http://127.0.0.1:3000",
]

# Configuración CORS para desarrollo (CAMBIAR EN PRODUCCIÓN)
CORS_ALLOW_ALL_ORIGINS = True  # Solo para desarrollo
CORS_ALLOW_CREDENTIALS = True  # Permitir cookies en peticiones cross-origin

# =============================================================================
# CONFIGURACIÓN DE API
# =============================================================================

# Configuración de URLs de API
APPEND_SLASH = False  # No agregar slash automáticamente a las URLs

# =============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO
# =============================================================================

# Configuración de almacenamiento de archivos estáticos
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

# Directorio para archivos de log
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configuración de logging para desarrollo y depuración
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'coofisam.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'coofisam': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'talento_cultura': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
