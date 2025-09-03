#!/bin/bash
# Script de inicio rápido para desarrolladores

echo "🚀 Coofisam360 - Quick Start"
echo "=========================="

# Mostrar rama actual
echo "Rama actual: $(git branch --show-current)"

# Mostrar estado
echo -e "\nEstado del repositorio:"
git status --short

echo -e "\nComandos disponibles:"
echo "1. Cambiar a tu rama: git checkout feature/tu-nombre-development"
echo "2. Actualizar con main: git pull origin main"
echo "3. Ir a Django: cd backend/django && source venv/bin/activate"
echo "4. Ejecutar Django: python manage.py runserver 0.0.0.0:8000"
echo "5. Ver ayuda completa: cat WORKFLOW.md"

echo -e "\n¿Necesitas ayuda? Lee el archivo WORKFLOW.md"
