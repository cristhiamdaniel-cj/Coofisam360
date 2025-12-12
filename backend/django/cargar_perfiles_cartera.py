from django.contrib.auth.models import User
from users.models import PerfilUsuario

# Usuarios del módulo de Cartera
usuarios_cartera = [
    {
        "username": "subgerenciacreditoycartera@coofisam.com",
        "responsable": "Emna Constanza Jaramillo Muñoz",
        "estructura": {
            "Cartera": {
                "Cartera": [
                    "Asignación Llamadas DG",
                    "Gestión Llamadas y Visitas Consolidado",
                    "Gestiones",
                    "Link de Llamadas",
                    "Link de Visitas",
                    "Seguimiento Campañas"
                ]
            }
        }
    },
    {
        "username": "coordinadoracartera@coofisam.com",
        "responsable": "Sandra Constanza Almario Gutiérrez",
        "estructura": {
            "Cartera": {
                "Cartera": [
                    "Asignación Llamadas DG",
                    "Gestión Llamadas y Visitas Consolidado",
                    "Gestiones",
                    "Link de Llamadas",
                    "Link de Visitas",
                    "Seguimiento Campañas"
                ]
            }
        }
    },
    {
        "username": "gestorcartera@coofisam.com",
        "responsable": "Daniela Yineth Suarez Llanos",
        "estructura": {
            "Cartera": {
                "Cartera": [
                    "Asignación Llamadas DG",
                    "Gestión Llamadas y Visitas Consolidado",
                    "Gestiones",
                    "Link de Llamadas",
                    "Link de Visitas",
                    "Seguimiento Campañas"
                ]
            }
        }
    }
]

# Crear o actualizar los usuarios de Cartera
for udata in usuarios_cartera:
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
    print(f"   📁 Módulo: Cartera")
    print()

print("=" * 60)
print("✅ Proceso completado exitosamente")
print(f"📊 Total de usuarios procesados: {len(usuarios_cartera)}")
print("=" * 60)
