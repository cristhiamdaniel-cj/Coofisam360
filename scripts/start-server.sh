#!/bin/bash

# Script para iniciar el servidor Django en el puerto 8060
# Coofisam360 - Sistema de Gestión Cooperativa

echo "🚀 Iniciando servidor Coofisam360 en puerto 8060..."
echo "================================================"

# Cambiar al directorio del proyecto Django
cd /home/desarrollo/coofisam360/backend/django

# Verificar que el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "❌ Error: Entorno virtual no encontrado en backend/django/venv"
    echo "   Ejecuta: python -m venv venv"
    exit 1
fi

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
source venv/bin/activate

# Verificar que Django está instalado
if ! python -c "import django" 2>/dev/null; then
    echo "❌ Error: Django no está instalado"
    echo "   Ejecuta: pip install -r ../requirements.txt"
    exit 1
fi

# Verificar migraciones pendientes
echo "🔍 Verificando migraciones..."
python manage.py showmigrations --plan | grep -q "\[ \]"
if [ $? -eq 0 ]; then
    echo "⚠️  Hay migraciones pendientes. Ejecutando migraciones..."
    python manage.py migrate
fi

# Iniciar servidor en puerto 8060
echo "🌐 Iniciando servidor Django en puerto 8060..."
echo "   URL local: http://localhost:8060"
echo "   URL admin: http://localhost:8060/admin"
echo "   Para ngrok: ngrok http 8060"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo "================================================"

# Ejecutar servidor Django
python manage.py runserver 0.0.0.0:8060

