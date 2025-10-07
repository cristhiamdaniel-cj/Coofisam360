from django.contrib.auth.models import User
from users.models import PerfilUsuario

usuarios_data = [
    {
        "username": "subgerenciainnovacion@coofisam.com",
        "responsable": "Nini Yohana Almario Santos",
        "estructura": {
            "Talento y Cultura": {
                "Formador Talento y Cultura": [
                    "Costo/Beneficio", "Formación y Participación", "Satisfacción del Aprendizaje",
                    "Transferencia del Conocimiento"
                ],
                "Sistema de Gestión de Seguridad y Salud en el Trabajo": [
                    "Accidentalidad", "Ausentismo", "Enfermedad Laboral", "Plan de Trabajo Anual",
                    "Programa de Capacitaciones", "Reporte Ministerio", "Restricciones Laborales"
                ],
                "Talento y Cultura": [
                    "Ascensos", "Bonificación", "Bono de Cumpleaños", "Clima Laboral",
                    "Desempeño", "Egresos", "Rol de Líder"
                ],
                "Disciplinario": [
                    "Control Disciplinario"
                ]
            }
        }
    },
    {
        "username": "talentohumano@coofisam.com",
        "responsable": "Joalber Pedreros Ramon",
        "estructura": {
            "Talento y Cultura": {
                "Formador Talento y Cultura": [
                    "Costo/Beneficio", "Formación y Participación", "Satisfacción del Aprendizaje",
                    "Transferencia del Conocimiento"
                ],
                "Sistema de Gestión de Seguridad y Salud en el Trabajo": [
                    "Accidentalidad", "Ausentismo", "Enfermedad Laboral", "Plan de Trabajo Anual",
                    "Programa de Capacitaciones", "Reporte Ministerio", "Restricciones Laborales"
                ],
                "Talento y Cultura": [
                    "Ascensos", "Bonificación", "Bono de Cumpleaños", "Clima Laboral",
                    "Desempeño", "Egresos", "Rol de Líder"
                ]
            }
        }
    },
    {
        "username": "formadortalentohumano@coofisam.com",
        "responsable": "Liliana Sterling Santofimio",
        "estructura": {
            "Talento y Cultura": {
                "Formador Talento y Cultura": [
                    "Costo/Beneficio", "Formación y Participación", "Satisfacción del Aprendizaje",
                    "Transferencia del Conocimiento"
                ]
            }
        }
    },
    {
        "username": "coordinadorsst@coofisam.com",
        "responsable": "Kety Dayana Roa Casanova",
        "estructura": {
            "Talento y Cultura": {
                "Sistema de Gestión de Seguridad y Salud en el Trabajo": [
                    "Accidentalidad", "Ausentismo", "Enfermedad Laboral", "Plan de Trabajo Anual",
                    "Programa de Capacitaciones", "Reporte Ministerio", "Restricciones Laborales"
                ]
            }
        }
    },
    {
        "username": "juridico01@coofisam.com",
        "responsable": "Estella Andrea González Elizalde",
        "estructura": {
            "Talento y Cultura": {
                "Disciplinario": [
                    "Control Disciplinario"
                ]
            }
        }
    }
]

for udata in usuarios_data:
    user, _ = User.objects.get_or_create(username=udata["username"])
    user.set_password("Coofisam123*")
    user.email = udata["username"]
    user.save()

    perfil, created = PerfilUsuario.objects.get_or_create(
        user=user,
        defaults={
            "responsable": udata["responsable"],
            "acceso_estructura": udata["estructura"]
        }
    )
    if not created:
        perfil.responsable = udata["responsable"]
        perfil.acceso_estructura = udata["estructura"]
        perfil.save()

    print(f"✅ Perfil de {udata['username']} actualizado/creado")

