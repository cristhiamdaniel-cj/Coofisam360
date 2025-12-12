#!/bin/bash

# Comando simple para iniciar Coofisam360 en puerto 8060
# Desde la carpeta del proyecto Django

cd /home/desarrollo/coofisam360/backend/django
source venv/bin/activate
python manage.py runserver 0.0.0.0:8060

