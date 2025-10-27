from django.contrib.auth.models import User
from users.models import PerfilUsuario

# Usuarios del módulo de Financiera
usuarios_financiera = [
    {
        "username": "subgerenciafinanciera@coofisam.com",
        "responsable": "Erik Fernando Rojas Vargas",
        "estructura": {
            "Financiera": {
                "Financiera": [
                    "Libro Balance",
                    "Categoría Oficinas",
                    "Cupo Crédito",
                    "Indicadores Financieros",
                    "Presupuesto",
                    "Textos Explicativos"
                ]
            }
        }
    },
    {
        "username": "contabilidad@coofisam.com",
        "responsable": "Marinela Perilla Capera",
        "estructura": {
            "Financiera": {
                "Financiera": [
                    "Libro Balance",
                    "Categoría Oficinas",
                    "Cupo Crédito",
                    "Indicadores Financieros",
                    "Presupuesto",
                    "Textos Explicativos"
                ]
            }
        }
    }
]

# Crear o actualizar los usuarios de Financiera
for udata in usuarios_financiera:
    user, created = User.objects.get_or_create(username=udata["username"])
    user.set_password("Coofisam123*")
    user.email = udata["username"]
    user.is_active = True
    user.is_staff = False
    user.is_superuser = False
    user.save()

    perfil, perfil_created = PerfilUsuario.objects.get_or_create(
        user=user,
        defaults={
            "responsable": udata["responsable"],
            "acceso_estructura": udata["estructura"]
        }
    )
    
    if not perfil_created:
        perfil.responsable = udata["responsable"]
        perfil.acceso_estructura = udata["estructura"]
        perfil.save()

    status = "creado" if created else "actualizado"
    print(f"✅ Usuario {udata['username']} {status}")
    print(f"   👤 Responsable: {udata['responsable']}")
    print(f"   📁 Módulo: Financiera")
    print()

print("=" * 60)
print("✅ Proceso completado exitosamente")
print(f"📊 Total de usuarios procesados: {len(usuarios_financiera)}")
print("=" * 60)

