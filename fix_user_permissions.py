#!/usr/bin/env python
import os
import sys

# Agregar el directorio del proyecto Django al path
sys.path.append('/home/desarrollo/coofisam360/backend/django')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coofisam_project.settings')

import django
django.setup()

from django.contrib.auth.models import User
from users.models import PerfilUsuario

def fix_user_permissions():
    try:
        # Obtener el usuario
        user = User.objects.get(username='cienciadatos@coofisam.com')
        print(f'Usuario encontrado: {user.username}')
        
        # Verificar o crear perfil
        perfil, created = PerfilUsuario.objects.get_or_create(
            user=user,
            defaults={
                'responsable': 'Ciencia de Datos',
                'acceso_estructura': ['modulo-financiero', 'modulo-cartera', 'modulo-credito', 'modulo-talento']
            }
        )
        
        if created:
            print('✅ Perfil creado con acceso completo')
        else:
            # Actualizar acceso existente
            perfil.acceso_estructura = ['modulo-financiero', 'modulo-cartera', 'modulo-credito', 'modulo-talento']
            perfil.save()
            print('✅ Perfil actualizado con acceso completo')
        
        print(f'Responsable: {perfil.responsable}')
        print(f'Acceso: {perfil.acceso_estructura}')
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    print('🔧 Configurando permisos de usuario...')
    success = fix_user_permissions()
    if success:
        print('✅ Configuración completada')
    else:
        print('❌ Error en la configuración')
        sys.exit(1)



