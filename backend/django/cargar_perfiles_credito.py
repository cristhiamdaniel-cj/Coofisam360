from django.contrib.auth.models import User
from users.models import PerfilUsuario

# Usuarios del módulo de Crédito
usuarios_credito = [
    {
        "username": "subgerenciacreditoycartera@coofisam.com",
        "responsable": "Emna Constanza Jaramillo Muñoz",
        "estructura": {
            "Credito": {
                "Credito": [
                    "Radicaciones de Crédito",
                    "Seguimiento Campañas Crédito por Oficina",
                    "Seguimiento Campañas Crédito"
                ]
            }
        },
        "actualizar": True  # Este usuario ya existe con Cartera
    },
    {
        "username": "directorcredito@coofisam.com",
        "responsable": "Álvaro López Rivera",
        "estructura": {
            "Credito": {
                "Credito": [
                    "Radicaciones de Crédito",
                    "Seguimiento Campañas Crédito por Oficina",
                    "Seguimiento Campañas Crédito"
                ]
            }
        },
        "actualizar": False
    },
    {
        "username": "analistacredito05@coofisam.com",
        "responsable": "Nubia Adriana Cano Silva",
        "estructura": {
            "Credito": {
                "Credito": [
                    "Radicaciones de Crédito",
                    "Seguimiento Campañas Crédito por Oficina",
                    "Seguimiento Campañas Crédito"
                ]
            }
        },
        "actualizar": False
    }
]

# Crear o actualizar los usuarios de Crédito
for udata in usuarios_credito:
    user, user_created = User.objects.get_or_create(username=udata["username"])
    
    if user_created:
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
    
    if not perfil_created and udata.get("actualizar", False):
        # Usuario ya existe (Emna), agregar Crédito manteniendo Cartera
        estructura_actual = perfil.acceso_estructura.copy()
        estructura_actual.update(udata["estructura"])
        perfil.acceso_estructura = estructura_actual
        perfil.save()
        print(f"✅ Usuario {udata['username']} actualizado")
        print(f"   👤 Responsable: {udata['responsable']}")
        print(f"   📁 Módulos: {', '.join(estructura_actual.keys())}")
        print()
    elif not perfil_created:
        # Actualizar completamente
        perfil.responsable = udata["responsable"]
        perfil.acceso_estructura = udata["estructura"]
        perfil.save()
        print(f"✅ Usuario {udata['username']} actualizado")
        print(f"   👤 Responsable: {udata['responsable']}")
        print(f"   📁 Módulo: Credito")
        print()
    else:
        # Usuario nuevo creado
        print(f"✅ Usuario {udata['username']} creado")
        print(f"   👤 Responsable: {udata['responsable']}")
        print(f"   📁 Módulo: Credito")
        print()

print("=" * 60)
print("✅ Proceso completado exitosamente")
print(f"📊 Total de usuarios procesados: {len(usuarios_credito)}")
print("=" * 60)
