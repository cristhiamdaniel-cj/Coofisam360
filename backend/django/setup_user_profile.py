#!/usr/bin/env python
"""
Script para configurar el perfil del usuario cienciadatos@coofisam.com
con acceso completo a todos los módulos.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coofisam_project.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import PerfilUsuario

def setup_user_profile():
    """Configurar el perfil del usuario con acceso completo"""
    
    try:
        # Obtener el usuario
        user = User.objects.get(username='cienciadatos@coofisam.com')
        print(f'✅ Usuario encontrado: {user.username}')
        print(f'   - Es staff: {user.is_staff}')
        print(f'   - Es superuser: {user.is_superuser}')
        
        # Verificar si ya tiene perfil
        try:
            perfil = PerfilUsuario.objects.get(user=user)
            print(f'✅ Perfil existente: {perfil.responsable}')
            print(f'   - Acceso estructura: {perfil.acceso_estructura}')
            
            # Actualizar con acceso completo
            perfil.acceso_estructura = [
                'modulo-financiero', 
                'modulo-cartera', 
                'modulo-credito', 
                'modulo-talento'
            ]
            perfil.save()
            print('✅ Perfil actualizado con acceso completo')
            
        except PerfilUsuario.DoesNotExist:
            print('⚠️  No tiene perfil creado')
            print('🔧 Creando perfil con acceso completo...')
            
            perfil = PerfilUsuario.objects.create(
                user=user,
                responsable='Ciencia de Datos',
                acceso_estructura=[
                    'modulo-financiero', 
                    'modulo-cartera', 
                    'modulo-credito', 
                    'modulo-talento'
                ]
            )
            print(f'✅ Perfil creado: {perfil.responsable}')
            print(f'   - Acceso estructura: {perfil.acceso_estructura}')
            
    except User.DoesNotExist:
        print('❌ Usuario cienciadatos@coofisam.com no encontrado')
        return False
        
    return True

if __name__ == '__main__':
    print('🚀 Configurando perfil de usuario...')
    print('=' * 50)
    
    success = setup_user_profile()
    
    if success:
        print('=' * 50)
        print('✅ Configuración completada exitosamente')
    else:
        print('=' * 50)
        print('❌ Error en la configuración')
        sys.exit(1)



