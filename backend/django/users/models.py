from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    responsable = models.CharField(max_length=200)

    # Estructura anidada: { "Carpeta": [ "Formulario1", "Formulario2", ... ] }
    acceso_estructura = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.user.username} - {self.responsable}"

