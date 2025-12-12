# 🚀 Guía de Desarrollo - Coofisam360

## 📋 Flujo de Trabajo

### Ramas Principales
- **`main`**: Rama principal (producción) - ⚠️ Solo administrador
- **`develop`**: Rama de desarrollo e integración
- **`feature/samir-development`**: Rama exclusiva para Samir
- **`feature/christiam-development`**: Rama exclusiva para Christiam

### Comandos para Desarrolladores

#### Iniciar trabajo diario
```bash
cd ~/coofisam360
git checkout feature/tu-nombre-development
git pull origin main  # Mantener actualizado
```

#### Trabajar en Django
```bash
cd backend/django
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

#### Guardar cambios
```bash
cd ~/coofisam360
git add .
git commit -m "feat: descripción clara de los cambios"
git push origin feature/tu-nombre-development
```

## 🛠️ Comandos de Django

### Servidor de desarrollo
```bash
python manage.py runserver 0.0.0.0:8060
```

### Migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### Usuarios
```bash
python manage.py createsuperuser
```

### Archivos estáticos
```bash
python manage.py collectstatic
```

## 📝 Convenciones de Commits

### Formato
```
tipo: descripción breve

Descripción detallada si es necesario
```

### Tipos
- `feat:` Nueva funcionalidad
- `fix:` Corrección de errores
- `docs:` Cambios en documentación
- `style:` Cambios de formato
- `refactor:` Refactorización
- `test:` Tests

### Ejemplos
```bash
git commit -m "feat: agregar modelo Cliente en users app"
git commit -m "fix: corregir error en login de usuarios"
git commit -m "docs: actualizar README con instrucciones"
```

## ⚠️ Reglas Importantes

### ❌ NO HACER
- Push directo a `main`
- Trabajar en rama de otro desarrollador
- Eliminar archivos sin consultar
- Cambios masivos sin documentar

### ✅ SÍ HACER
- Trabajar solo en tu rama asignada
- Commits frecuentes y descriptivos
- Probar código antes de push
- Comunicar cambios importantes
- Mantener rama actualizada con main

## 🆘 Comandos de Emergencia

### Ver estado actual
```bash
git status
git log --oneline -5
```

### Deshacer último commit (sin perder cambios)
```bash
git reset --soft HEAD~1
```

### Deshacer cambios no guardados
```bash
git restore .
```

### Cambiar a main si hay problemas
```bash
git checkout main
```

## 🔧 Configuración del Entorno

### Backend
```bash
cd backend/django
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
```


## 📊 Estructura de Archivos

```
coofisam360/
├── backend/
│   ├── django/              # Proyecto Django
│   ├── requirements.txt     # Dependencias
│   └── env.example         # Variables de entorno
├── database/               # Scripts de BD
├── docs/                   # Documentación
├── scripts/                # Scripts de utilidad
└── README.md              # Documentación principal
```

## 🐛 Debugging

### Logs de Django
```bash
# Ver logs en tiempo real
tail -f backend/django/logs/django.log
```

### Debug en desarrollo
```python
# En settings.py
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## 📈 Testing

### Ejecutar tests
```bash
python manage.py test
```

### Tests específicos
```bash
python manage.py test users.tests
python manage.py test consultasSQL.tests
```

## 🚀 Deployment

### Preparar para producción
```bash
# Instalar dependencias de producción
pip install -r requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Aplicar migraciones
python manage.py migrate
```

### Variables de entorno de producción
```env
DEBUG=False
SECRET_KEY=clave-secreta-fuerte
ALLOWED_HOSTS=tu-dominio.com
DATABASE_URL=postgresql://usuario:password@host:5432/db
```

---

**Para más información, consulta el [README principal](../README.md)**
