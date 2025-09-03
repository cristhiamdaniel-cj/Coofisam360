# 🚀 Flujo de Trabajo - Coofisam360

## 📁 Estructura del Proyecto
```
coofisam360/
├── backend/
│   ├── django/              # ✅ Aplicación Django migrada
│   │   ├── Coofisam/        # App principal
│   │   ├── coofisam_project/ # Configuración Django  
│   │   ├── users/           # Gestión de usuarios
│   │   ├── manage.py        # Comando Django
│   │   ├── db.sqlite3       # Base de datos
│   │   ├── static/          # Archivos estáticos
│   │   └── staticfiles/     # Archivos estáticos compilados
│   ├── requirements.txt     # Dependencias Python
│   └── src/                 # Código fuente adicional
├── frontend/                # Frontend (React/Vue/Angular)
├── database/
│   ├── consultasSQL/        # ✅ Consultas SQL migradas
│   ├── scripts/             # Scripts de BD
│   └── seeds/               # Datos iniciales
├── docs/                    # Documentación del proyecto
├── bi/                      # Business Intelligence
└── README.md
```

## 🌿 Ramas de Trabajo

### Ramas Principales
- **`main`**: Rama principal (producción) - ⚠️ Solo administrador
- **`develop`**: Rama de desarrollo e integración
- **`feature/samir-development`**: Rama exclusiva para Samir
- **`feature/christiam-development`**: Rama exclusiva para Christiam

### Política de Ramas
- ✅ Cada desarrollador trabaja SOLO en su rama
- ✅ Los cambios se integran via Pull Request
- ❌ NO hacer push directo a `main`
- ✅ Mantener ramas actualizadas con `main`

## 👨‍💻 Comandos para Samir

### Iniciar trabajo en tu rama:
```bash
cd ~/coofisam360
git checkout feature/samir-development
git pull origin main  # Mantener actualizado con main
```

### Trabajar en el proyecto Django:
```bash
cd backend/django
# Activar entorno virtual
source venv/bin/activate
# Trabajar normalmente con Django
python manage.py runserver
# Hacer cambios, crear modelos, vistas, etc.
```

### Guardar cambios:
```bash
cd ~/coofisam360
git add .
git commit -m "feat: descripción clara de los cambios realizados"
git push origin feature/samir-development
```

### Actualizar rama con cambios de main:
```bash
git checkout feature/samir-development
git pull origin main
# Resolver conflictos si existen
git push origin feature/samir-development
```

## 👨‍💻 Comandos para Christiam

### Iniciar trabajo en tu rama:
```bash
cd ~/coofisam360
git checkout feature/christiam-development
git pull origin main  # Mantener actualizado con main
```

### Trabajar en el proyecto Django:
```bash
cd backend/django
# Activar entorno virtual
source venv/bin/activate
# Trabajar normalmente con Django
python manage.py runserver
# Hacer cambios, crear modelos, vistas, etc.
```

### Guardar cambios:
```bash
cd ~/coofisam360
git add .
git commit -m "feat: descripción clara de los cambios realizados"
git push origin feature/christiam-development
```

### Actualizar rama con cambios de main:
```bash
git checkout feature/christiam-development
git pull origin main
# Resolver conflictos si existen
git push origin feature/christiam-development
```

## 🔄 Proceso de Integración

### Para integrar cambios a main:
1. **Desarrollador**: Push a su rama feature
2. **Administrador**: Revisa cambios y hace merge a main
3. **Todos**: Actualizan sus ramas con los nuevos cambios de main

### Comandos para el administrador (desarrollo):
```bash
# Revisar cambios de Samir
git checkout feature/samir-development
git pull origin feature/samir-development
# Revisar código...

# Integrar a main
git checkout main
git merge feature/samir-development
git push origin main

# Repetir para Christiam si es necesario
```

## 🛠️ Comandos de Django Importantes

### Ejecutar servidor de desarrollo:
```bash
cd ~/coofisam360/backend/django
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Aplicar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Crear superusuario:
```bash
python manage.py createsuperuser
```

### Recolectar archivos estáticos:
```bash
python manage.py collectstatic
```

## 📝 Convenciones de Commits

### Formato:
```
tipo: descripción breve

Descripción más detallada si es necesario
```

### Tipos de commit:
- `feat:` Nueva funcionalidad
- `fix:` Corrección de errores  
- `docs:` Cambios en documentación
- `style:` Cambios de formato/estilo
- `refactor:` Refactorización de código
- `test:` Agregar o modificar tests

### Ejemplos:
```bash
git commit -m "feat: agregar modelo de Cliente en users app"
git commit -m "fix: corregir error en login de usuarios"
git commit -m "docs: actualizar README con instrucciones de instalación"
```

## 🚨 Reglas Importantes

### ❌ NO HACER:
- Push directo a `main`
- Trabajar en la rama de otro desarrollador
- Eliminar archivos sin consultar
- Cambios masivos sin documentar

### ✅ SÍ HACER:
- Trabajar solo en tu rama asignada
- Hacer commits frecuentes y descriptivos
- Probar código antes de hacer push
- Comunicar cambios importantes al equipo
- Mantener tu rama actualizada con main

## 🆘 Comandos de Emergencia

### Si algo sale mal con Git:
```bash
# Ver estado actual
git status
git log --oneline -5

# Deshacer último commit (sin perder cambios)
git reset --soft HEAD~1

# Deshacer cambios no guardados
git restore .

# Cambiar a main si hay problemas
git checkout main
```

### Si necesitas ayuda:
1. Revisar este archivo WORKFLOW.md
2. Consultar con el administrador (desarrollo)  
3. Usar `git status` para ver el estado actual
