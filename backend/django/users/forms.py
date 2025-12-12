"""
Coofisam360 - Formularios de Usuarios

Formularios para la gestión de usuarios en el sistema Coofisam360.
Incluye formularios de autenticación y gestión de perfiles.

Autor: Equipo de Desarrollo Coofisam360
Versión: 1.0
"""

from django import forms


class LoginForm(forms.Form):
    """
    Formulario de inicio de sesión para usuarios del sistema.
    
    Permite a los usuarios autenticarse con su nombre de usuario y contraseña.
    """
    
    username = forms.CharField(
        max_length=100, 
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nombre de usuario'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña'
        }), 
        label='Contraseña'
    )
    
    class Meta:
        fields = ['username', 'password']
