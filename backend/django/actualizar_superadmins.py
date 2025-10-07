from django.contrib.auth.models import User
from users.models import PerfilUsuario

# Lista de superadmins definitivos con responsables corregidos
superadmins_data = [
    {
        "username": "lider.tecnico@neusisolutions.com",
        "password": "Neusi2025*",
        "responsable": "Equipo de Desarrollo de NEUSI",
    },
    {
        "username": "cienciadatos@coofisam.com",
        "password": "Coofisam2025*",
        "responsable": "Jorge Eduardo Plazas Diaz",
    },
]

# Estructura de acceso completa
estructura_completa = {
    "Financiera": {},
    "Talento y Cultura": {
        "Disciplinario": ["Control Disciplinario"],
        "Talento y Cultura": [
            "Ascensos", "Bonificación", "Bono de Cumpleaños",
            "Clima Laboral", "Desempeño", "Egresos", "Rol de Líder"
        ],
        "Formador Talento y Cultura": [
            "Costo/Beneficio", "Formación y Participación",
            "Satisfacción del Aprendizaje", "Transferencia del Conocimiento"
        ],
        "Sistema de Gestión de Seguridad y Salud en el Trabajo": [
            "Accidentalidad", "Ausentismo", "Enfermedad Laboral",
            "Plan de Trabajo Anual", "Programa de Capacitaciones",
            "Reporte Ministerio", "Restricciones Laborales"
        ]
    },
    "Cartera": {},
    "Credito": {},
    "Comercial": {},
    "Gestion Documental": {},
    "Ingenieria Organizacional": {},
    "Juridico": {},
    "Oficial de Cumplimiento": {},
}

# Crear o actualizar los superadmins
for data in superadmins_data:
    user, _ = User.objects.get_or_create(username=data["username"])
    user.set_password(data["password"])
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()

    perfil, created = PerfilUsuario.objects.get_or_create(
        user=user,
        defaults={
            "responsable": data["responsable"],
            "acceso_estructura": estructura_completa
        }
    )
    if not created:
        perfil.responsable = data["responsable"]
        perfil.acceso_estructura = estructura_completa
        perfil.save()

    print(f"✅ Perfil actualizado para {data['username']} con responsable {data['responsable']}")

