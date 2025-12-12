# 🏦 Coofisam360 - Sistema de Gestión Cooperativa

Sistema integral de gestión para cooperativas financieras desarrollado con Django.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Tecnologías](#tecnologías)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Desarrollo](#desarrollo)
- [Contribución](#contribución)

## ✨ Características

- **Gestión de Usuarios**: Sistema completo de autenticación y autorización
- **Dashboard Principal**: Panel de control con métricas clave
- **Gestión de Socios**: Administración de miembros de la cooperativa
- **Cuentas de Ahorros**: Control de depósitos y retiros
- **Créditos y Préstamos**: Gestión de productos crediticios
- **Tesorería**: Control de flujo de caja
- **Contabilidad**: Registro contable automatizado
- **Reportes Financieros**: Generación de informes
- **Auditoría**: Trazabilidad de operaciones
- **Business Intelligence**: Análisis de datos

## 🛠️ Tecnologías

### Backend
- **Django 5.2.5**: Framework web principal
- **Django REST Framework**: API REST
- **PostgreSQL**: Base de datos principal
- **Gunicorn**: Servidor WSGI
- **WhiteNoise**: Servir archivos estáticos

### Herramientas
- **Git**: Control de versiones
- **Docker**: Containerización (opcional)

## 📁 Estructura del Proyecto

```
coofisam360/
├── backend/                    # Backend Django
│   ├── django/                # Proyecto Django principal
│   │   ├── Coofisam/         # App principal
│   │   ├── coofisam_project/ # Configuración Django
│   │   ├── users/            # Gestión de usuarios
│   │   ├── consultasSQL/     # Consultas y reportes
│   │   └── manage.py         # Comando Django
│   ├── requirements.txt      # Dependencias Python
│   ├── requirements-dev.txt  # Dependencias de desarrollo
│   └── env.example          # Variables de entorno ejemplo
├── database/                # Base de datos
│   ├── scripts/             # Scripts de BD
│   └── seeds/               # Datos iniciales
├── docs/                    # Documentación
├── scripts/                 # Scripts de utilidad
├── bi/                      # Business Intelligence
└── README.md               # Este archivo
```

## 🚀 Instalación

### Prerrequisitos

- Python 3.12+
- Node.js 18+
- PostgreSQL 13+
- Git

### Backend (Django)

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd coofisam360
   ```

2. **Configurar entorno virtual**:
   ```bash
   cd backend/django
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r ../requirements.txt
   ```

4. **Configurar variables de entorno**:
   ```bash
   cp ../env.example .env
   # Editar .env con tus configuraciones
   ```

5. **Configurar base de datos**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Ejecutar servidor**:
   ```bash
   python manage.py runserver 0.0.0.0:8060
   ```


## ⚙️ Configuración

### Variables de Entorno

Copia `backend/env.example` a `backend/.env` y configura:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta
DATABASE_URL=postgresql://usuario:password@localhost:5432/coofisam360
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Base de Datos

El sistema está configurado para usar PostgreSQL. Asegúrate de:

1. Crear la base de datos
2. Configurar las credenciales en `.env`
3. Ejecutar las migraciones

## 🎯 Uso

### Acceso al Sistema

- **Backend API**: http://localhost:8060
- **Admin Django**: http://localhost:8060/admin

### Módulo Financiero (API v1)

- Oficinas
  - GET/POST/DELETE `/api/v1/finanzas/oficinas/` y `/api/v1/finanzas/oficinas/<codigo>/`
- Cupos de crédito
  - GET/POST/DELETE `/api/v1/finanzas/cupos-credito/`
- Indicadores comparativa
  - GET/POST/PUT/DELETE `/api/v1/indicadores/comparativa/`
  - GET catálogo `/api/v1/indicadores/disponibles/`
- Presupuesto App (dataset para UI)
  - GET/POST/PUT/DELETE `/api/v1/finanzas/presupuesto-app/`
  - Upload simple: `POST /api/v1/finanzas/presupuesto/upload-simple/`
  - Files: `GET /api/v1/finanzas/presupuesto/files/` · Execute: `POST /api/v1/finanzas/presupuesto/execute-file/`
- Ejecución presupuestal (PUC 6 dígitos)
  - GET/POST/DELETE `/api/v1/finanzas/ejecucion-presupuestal/`
  - Upload: `POST /api/v1/finanzas/ejecucion-presupuestal/upload/`
  - Files: `GET /api/v1/finanzas/ejecucion-presupuestal/files/`
- Archivos
  - Descargar: `GET /api/v1/finanzas/download/?path=...`
  - Eliminar: `DELETE /api/v1/finanzas/delete/` (body JSON `{ path }`)

Autenticación
- Token DRF `Authorization: Token <token>`
- Endpoints de login/me: `/api/v1/auth/login/`, `/api/v1/me/`

### Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic

# Ejecutar tests
python manage.py test
```

## 👨‍💻 Desarrollo

### Flujo de Trabajo

1. **Crear rama de feature**:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. **Desarrollar y probar**:
   ```bash
   # Hacer cambios
   python manage.py test
   ```

3. **Commit y push**:
   ```bash
   git add .
   git commit -m "feat: descripción del cambio"
   git push origin feature/nueva-funcionalidad
   ```

4. **Crear Pull Request**

### Convenciones

- **Commits**: Usar formato `tipo: descripción`
- **Ramas**: `feature/`, `fix/`, `docs/`
- **Código**: Seguir PEP 8 (Python)

## 📚 Documentación

- [Guía de Desarrollo](docs/README.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guide](docs/contributing.md)

### Docker backend (opcional)
- Build: `docker build -t coofisam360-backend backend`
- Run: `docker run --rm -p 8060:8060 coofisam360-backend`

## 🤝 Contribución

1. Fork el proyecto
2. Crea tu rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:

- **Email**: soporte@coofisam360.com
- **Documentación**: [docs/](docs/)
- **Issues**: [GitHub Issues](repository-url/issues)

---

**Desarrollado con ❤️ para Coofisam**
