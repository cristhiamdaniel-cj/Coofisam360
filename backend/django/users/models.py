"""
Coofisam360 - Modelos de Usuarios

Modelos para la gestión de usuarios y perfiles en el sistema Coofisam360.
Extiende el modelo de usuario de Django con información específica del negocio.

Autor: Equipo de Desarrollo Coofisam360
Versión: 1.0
"""

from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    """
    Modelo que extiende el usuario de Django con información específica del negocio.
    
    Este modelo almacena información adicional del usuario como el responsable
    y la estructura de acceso a formularios del sistema.
    """
    
    # Relación uno a uno con el modelo User de Django
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="perfil",
        verbose_name="Usuario"
    )
    
    # Nombre del responsable o cargo del usuario
    responsable = models.CharField(
        max_length=200,
        verbose_name="Responsable",
        help_text="Nombre del responsable o cargo del usuario"
    )

    # Estructura de acceso a formularios del sistema
    # Formato: { "Carpeta": [ "Formulario1", "Formulario2", ... ] }
    acceso_estructura = models.JSONField(
        default=dict,
        verbose_name="Estructura de Acceso",
        help_text="Estructura anidada que define los formularios accesibles por carpeta"
    )

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        db_table = "users_perfilusuario"

    def __str__(self):
        """Representación en string del perfil de usuario"""
        return f"{self.user.username} - {self.responsable}"

