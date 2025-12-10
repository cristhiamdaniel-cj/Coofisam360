"""
*********************************************
*    Módulo API: Usuarios y Finanzas         *
*********************************************
Bloques de endpoints para autenticación y
el módulo financiero (oficinas, indicadores,
presupuesto-app y ejecución presupuestal).
"""
from rest_framework import generics, status
import logging
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.conf import settings
from .serializers import UserSerializer, UserCreateSerializer
from rest_framework.authtoken.models import Token
from pathlib import Path
import os
import re
import unicodedata
from datetime import datetime, timedelta
from django.db import connections, transaction
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import PerfilUsuario
from users.serializers import PerfilUsuarioSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from users.models import PerfilUsuario
from users.serializers import PerfilUsuarioSerializer

# Helper para ejecutar SQL evitando errores por parámetros vacíos o tipo incorrecto
def _exec(cursor, sql, params=None):
    """Ejecuta SQL de forma segura:
    - Si params es dict vacío o no hay placeholders nombrados, no lo pasa.
    - Si params es lista/tupla y no hay %s en el SQL, no lo pasa.
    - Caso contrario, delega a cursor.execute(sql, params).
    """
    if params is None:
        return cursor.execute(sql)
    # Mapping params with named placeholders
    if isinstance(params, dict):
        if not params or '%(' not in sql:
            return cursor.execute(sql)
        return cursor.execute(sql, params)
    # Sequence params with positional placeholders
    if isinstance(params, (list, tuple)):
        if '%s' not in sql:
            return cursor.execute(sql)
        return cursor.execute(sql, params)
    # Fallback: let psycopg2 handle/raise
    return cursor.execute(sql, params)

# Helper para normalizar fechas recibidas como texto a 'YYYY-MM-DD'
def _to_iso_date(s: str | None) -> str | None:
    if not s:
        return None
    try:
        st = str(s).strip()
        # Formato DD/MM/YYYY
        if '/' in st and '-' not in st:
            d, m, y = st.split('/')
            if len(y) == 4:
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        # Formato YYYY-MM-DD
        if '-' in st:
            parts = st.split('-')
            if len(parts) >= 3 and len(parts[0]) == 4:
                y, m, d = parts[:3]
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        # Fallback: devolver original
        return st
    except Exception:
        return s
class PerfilUsuarioListView(ListAPIView):
    queryset = PerfilUsuario.objects.all()
    serializer_class = PerfilUsuarioSerializer
    permission_classes = [IsAdminUser]  # solo staff o superusuarios

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mi_perfil(request):
    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        serializer = PerfilUsuarioSerializer(perfil)
        return Response(serializer.data)
    except PerfilUsuario.DoesNotExist:
        return Response({"error": "Perfil no encontrado"}, status=404)


@api_view(["POST"])
@permission_classes([AllowAny])
def custom_login(request):
    """
    Endpoint personalizado de login que devuelve JSON.
    Compatible con el frontend que espera respuesta JSON.
    """
    # Manejar tanto JSON como form-data
    if request.content_type == 'application/json':
        username = request.data.get('username')
        password = request.data.get('password')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')

    if not username or not password:
        return Response({
            "error": "Username y password son requeridos"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Autenticar usuario
    user = authenticate(username=username, password=password)

    if user is not None:
        # Obtener o crear token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser
            },
            "message": "Login exitoso"
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "error": "Credenciales inválidas"
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Endpoint para obtener información del usuario autenticado.
    Compatible con el frontend que necesita datos del usuario después del login.
    """
    user = request.user
    
    # Obtener perfil de usuario si existe
    try:
        from .models import PerfilUsuario
        perfil = PerfilUsuario.objects.get(user=user)
        responsable = perfil.responsable
        acceso_estructura = perfil.acceso_estructura if hasattr(perfil, 'acceso_estructura') else []
    except:
        responsable = f"{user.first_name} {user.last_name}".strip() or user.username
        acceso_estructura = []
    
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "responsable": responsable,
        "acceso_estructura": acceso_estructura
    }, status=status.HTTP_200_OK)

# ====== Helpers de detección de vistas por esquema ======
def _view_exists(schema: str, view: str) -> bool:
    with connections['default'].cursor() as c:
        c.execute(
            """
            SELECT 1 FROM information_schema.views
            WHERE table_schema=%s AND table_name=%s
            """,
            [schema, view],
        )
        return c.fetchone() is not None

def _choose_view(candidates):
    """Recibe lista de (schema, view). Retorna 'schema.view' de la primera que exista o None."""
    for schema, view in candidates:
        try:
            if _view_exists(schema, view):
                return f"{schema}.{view}"
        except Exception:
            continue
    return None


def _ensure_indicadores_comparativa_table():
    """Garantiza que indicadores.indicadores_comparativa exista con columnas nuevas."""
    with connections['default'].cursor() as c:
        c.execute("CREATE SCHEMA IF NOT EXISTS indicadores;")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS indicadores.indicadores_comparativa (
              nombre_indicador text NOT NULL,
              anio int NOT NULL,
              mes int NOT NULL,
              periodo text,
              alcance text,
              valor_indicador numeric,
              mes_de_diciembre_fijo numeric,
              anio_menos_1_dic numeric,
              periodo2 text,
              valor_indicador_2 numeric,
              anio_menos_1 int,
              mismo_mes_ref_1 int,
              periodo3 text,
              valor_indicador_3 numeric,
              anio_menos_2 int,
              mismo_mes_ref_2 int,
              periodo4 text,
              valor_indicador_4 numeric,
              analisis text,
              codigo int,
              saldo_c14 numeric,
              saldo_c21 numeric,
              CONSTRAINT indicadores_comparativa_pk PRIMARY KEY (nombre_indicador, anio, mes)
            )
            """
        )
        c.execute(
            "ALTER TABLE indicadores.indicadores_comparativa ADD COLUMN IF NOT EXISTS codigo int;"
        )
        c.execute(
            "ALTER TABLE indicadores.indicadores_comparativa ADD COLUMN IF NOT EXISTS saldo_c14 numeric;"
        )
        c.execute(
            "ALTER TABLE indicadores.indicadores_comparativa ADD COLUMN IF NOT EXISTS saldo_c21 numeric;"
        )
        c.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_ic_codigo_anio_mes'
                  AND conrelid = 'indicadores.indicadores_comparativa'::regclass
              ) THEN
                ALTER TABLE indicadores.indicadores_comparativa
                  ADD CONSTRAINT uq_ic_codigo_anio_mes UNIQUE (codigo, anio, mes);
              END IF;
            END;
            $$;
            """
        )


def _refresh_oficina_saldos(anio: int | None = None, mes: int | None = None, codigo: int | None = None, logger: logging.Logger | None = None) -> None:
    """Sincroniza saldo_c14 y saldo_c21 desde saldos_agencia por oficina."""
    _ensure_indicadores_comparativa_table()

    filters = [
        "NULLIF(TRIM(sa.agencia_codigo::text), '') ~ '^-?[0-9]+'"
    ]
    params: dict[str, object] = {}
    if anio is not None:
        params['anio'] = anio
        filters.append('sa.anio = %(anio)s::int')
    if mes is not None:
        params['mes'] = mes
        filters.append('sa.mes = %(mes)s::int')
    if codigo is not None:
        params['codigo_raw'] = str(codigo)
        filters.append("NULLIF(TRIM(sa.agencia_codigo::text), '') = %(codigo_raw)s")

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ''

    sql = f"""
        WITH src AS (
            SELECT
                NULLIF(TRIM(sa.agencia_codigo::text),'')::int AS codigo,
                sa.anio::int AS anio,
                sa.mes::int AS mes,
                SUM(sa.saldo_final) FILTER (
                    WHERE NULLIF(TRIM(sa.cuenta::text),'') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                      AND NULLIF(TRIM(sa.cuenta::text),'')::numeric = 14
                ) AS saldo_c14,
                SUM(sa.saldo_final) FILTER (
                    WHERE NULLIF(TRIM(sa.cuenta::text),'') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                      AND NULLIF(TRIM(sa.cuenta::text),'')::numeric = 21
                ) AS saldo_c21
            FROM saldos_agencia sa
            {where_sql}
            GROUP BY 1, 2, 3
        ),
        prepared AS (
            SELECT
                s.codigo,
                s.anio,
                s.mes,
                LPAD(s.anio::text, 4, '0') || '-' || LPAD(s.mes::text, 2, '0') AS periodo,
                CONCAT('__OFICINA__:', LPAD(s.codigo::text, 3, '0')) AS nombre_indicador,
                COALESCE(s.saldo_c14, 0) AS saldo_c14,
                COALESCE(s.saldo_c21, 0) AS saldo_c21
            FROM src s
            WHERE s.codigo IS NOT NULL
        )
        INSERT INTO indicadores.indicadores_comparativa (codigo, anio, mes, periodo, nombre_indicador, saldo_c14, saldo_c21)
        SELECT
            p.codigo,
            p.anio,
            p.mes,
            p.periodo,
            p.nombre_indicador,
            p.saldo_c14,
            p.saldo_c21
        FROM prepared p
        ON CONFLICT (codigo, anio, mes) DO UPDATE
        SET periodo = EXCLUDED.periodo,
            nombre_indicador = EXCLUDED.nombre_indicador,
            saldo_c14 = EXCLUDED.saldo_c14,
            saldo_c21 = EXCLUDED.saldo_c21;
    """

    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
    except Exception:
        if logger:
            logger.exception('[comparativa] Error al sincronizar saldos por oficina')
        else:
            raise


def _refresh_global_indicadores(anio: int | None = None, mes: int | None = None, logger: logging.Logger | None = None) -> None:
    """Replica indicadores consolidados del datamart hacia indicadores.indicadores_comparativa."""
    if anio is None or mes is None:
        return

    periodo_str = f"{anio:04d}-{mes:02d}"
    _ensure_indicadores_comparativa_table()

    sql = (
        """
        WITH src AS (
            SELECT
              v.nombre_indicador::text AS nombre_indicador,
              %(anio)s::int AS anio,
              %(mes)s::int AS mes,
              COALESCE(NULLIF(TRIM(v.periodo), ''), %(periodo)s)::text AS periodo,
              CASE WHEN NULLIF(TRIM(v.alcance), '') IS NULL THEN NULL
                   ELSE convert_from(convert_to(NULLIF(TRIM(v.alcance), ''), 'WIN1252'), 'UTF8')
              END::text AS alcance,
              v.valor_indicador::numeric,
              NULLIF(TRIM(v.mes_de_diciembre_fijo), '')::text AS mes_de_diciembre_fijo,
              v.anio_menos_1_dic::int AS anio_menos_1_dic,
              NULLIF(TRIM(v.periodo2), '')::text AS periodo2,
              v.valor_indicador_2::numeric,
              v.anio_menos_1::int AS anio_menos_1,
              NULLIF(TRIM(v.mismo_mes_ref_1), '')::text AS mismo_mes_ref_1,
              NULLIF(TRIM(v.periodo3), '')::text AS periodo3,
              v.valor_indicador_3::numeric,
              v.anio_menos_2::int AS anio_menos_2,
              NULLIF(TRIM(v.mismo_mes_ref_2), '')::text AS mismo_mes_ref_2,
              NULLIF(TRIM(v.periodo4), '')::text AS periodo4,
              v.valor_indicador_4::numeric,
              NULLIF(TRIM(v.analisis), '')::text AS analisis,
              NULLIF(TRIM(v.mes), '')::text AS mes_nombre,
              make_date(%(anio)s::int, %(mes)s::int, 1) AS fecha,
              %(mes)s::int AS mes_orden
            FROM indicadores.vista_indicadores_comparativa v
            WHERE v.anio = %(anio)s::int
              AND COALESCE(NULLIF(TRIM(v.periodo), ''), %(periodo)s) = %(periodo)s
        )
        INSERT INTO indicadores.indicadores_comparativa (
            nombre_indicador,
            anio,
            mes,
            periodo,
            alcance,
            valor_indicador,
            mes_de_diciembre_fijo,
            anio_menos_1_dic,
            periodo2,
            valor_indicador_2,
            anio_menos_1,
            mismo_mes_ref_1,
            periodo3,
            valor_indicador_3,
            anio_menos_2,
            mismo_mes_ref_2,
            periodo4,
            valor_indicador_4,
            analisis,
            mes_nombre,
            mes_orden,
            fecha
        )
        SELECT
            nombre_indicador,
            anio,
            mes,
            periodo,
            alcance,
            valor_indicador,
            mes_de_diciembre_fijo,
            anio_menos_1_dic,
            periodo2,
            valor_indicador_2,
            anio_menos_1,
            mismo_mes_ref_1,
            periodo3,
            valor_indicador_3,
            anio_menos_2,
            mismo_mes_ref_2,
            periodo4,
            valor_indicador_4,
            analisis,
            mes_nombre,
            mes_orden,
            fecha
        FROM src
        ON CONFLICT (lower(trim(nombre_indicador)), substring(trim(periodo) from 1 for 7)) DO UPDATE
        SET
            valor_indicador = EXCLUDED.valor_indicador,
            mes_de_diciembre_fijo = EXCLUDED.mes_de_diciembre_fijo,
            anio_menos_1_dic = EXCLUDED.anio_menos_1_dic,
            periodo2 = EXCLUDED.periodo2,
            valor_indicador_2 = EXCLUDED.valor_indicador_2,
            anio_menos_1 = EXCLUDED.anio_menos_1,
            mismo_mes_ref_1 = EXCLUDED.mismo_mes_ref_1,
            periodo3 = EXCLUDED.periodo3,
            valor_indicador_3 = EXCLUDED.valor_indicador_3,
            anio_menos_2 = EXCLUDED.anio_menos_2,
            mismo_mes_ref_2 = EXCLUDED.mismo_mes_ref_2,
            periodo4 = EXCLUDED.periodo4,
            valor_indicador_4 = EXCLUDED.valor_indicador_4,
            alcance = COALESCE(EXCLUDED.alcance, indicadores.indicadores_comparativa.alcance),
            anio = EXCLUDED.anio,
            mes = EXCLUDED.mes,
            periodo = EXCLUDED.periodo,
            mes_nombre = COALESCE(EXCLUDED.mes_nombre, indicadores.indicadores_comparativa.mes_nombre),
            mes_orden = EXCLUDED.mes_orden,
            fecha = EXCLUDED.fecha,
            analisis = CASE
                WHEN COALESCE(indicadores.indicadores_comparativa.analisis, '') <> '' THEN indicadores.indicadores_comparativa.analisis
                ELSE EXCLUDED.analisis
            END
        ;
        """
    )

    params = {'anio': anio, 'mes': mes, 'periodo': periodo_str}
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
    except Exception:
        if logger:
            logger.exception('[comparativa] Error al refrescar indicadores consolidados')
        else:
            raise
class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    return Response({
        'status': 'API funcionando correctamente',
        'version': '1.0',
        'mensaje': 'API lista para desarrollo frontend',
        'endpoints': {
            'publicos': [
                '/api/v1/status/',
                '/api/v1/users/ (GET, POST)',
            ],
            'autenticados': [
                '/api/v1/profile/',
                '/api/v1/users/{id}/ (GET, PUT, DELETE)'
            ]
        },
        'autenticacion': {
            'tipo': 'Token',
            'header': 'Authorization: Token tu_token_aqui',
            'ejemplo_token': 'a4c54ef00b2fc005a533c137d153949871f12f22'
        }
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def api_test_data(request):
    """Endpoint de prueba con datos mock para el frontend"""
    return Response({
        'usuarios_ejemplo': [
            {'id': 1, 'nombre': 'Juan Pérez', 'email': 'juan@coofisam.com'},
            {'id': 2, 'nombre': 'María González', 'email': 'maria@coofisam.com'}
        ],
        'configuracion': {
            'cors_habilitado': True,
            'base_url': 'http://IP_SERVIDOR:8000/api/v1/'
        }
    })

# ====== Utilidades módulo financiero ======

def _norm(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()

def _fix_encoding(text: str | None) -> str | None:
    """Corrige casos comunes de mojibake (UTF-8 leído como latin1/win1252).
    Se aplica sólo si se detectan caracteres sospechosos como 'Ã' o 'Â'.
    """
    if text is None:
        return None
    s = str(text)
    if 'Ã' in s or 'Â' in s:
        try:
            return s.encode('latin1', errors='ignore').decode('utf-8', errors='ignore') or s
        except Exception:
            return s
    return s

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'setiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}

FNAME_RE = re.compile(
    r'listado[\s_-]*balances[\s_-]*consolidado[\s_-]*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)[\s_-]*(\d{4})\.(xlsx|xls)$',
    re.IGNORECASE
)

def _get_balance_root() -> Path:
    # Preferir carpeta de subidos definida en settings
    root = getattr(settings, 'LIBRO_BALANCE_ROOT', None)
    if root:
        return Path(root)
    # Fallback relativo al proyecto
    return Path(settings.BASE_DIR) / 'Coofisam' / 'data' / 'Libro_de_Balance_subidos'

def _build_tree(root: Path, path: Path, max_depth: int = 3, include_files: bool = True, _depth: int = 0):
    """Construye árbol con rutas relativas (rel) seguras desde root."""
    rel = path.relative_to(root) if path != root else Path("")
    node = {"name": path.name or str(path), "type": "dir", "children": [], "rel": rel.as_posix()}
    if _depth >= max_depth:
        return node
    try:
        with os.scandir(path) as it:
            entries = sorted(it, key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
            for entry in entries:
                entry_path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    node["children"].append(_build_tree(root, entry_path, max_depth, include_files, _depth + 1))
                elif include_files:
                    node["children"].append({
                        "name": entry.name,
                        "type": "file",
                        "rel": entry_path.relative_to(root).as_posix(),
                    })
    except FileNotFoundError:
        node["error"] = f"Ruta no existe: {path}"
    except PermissionError:
        node["children"].append({"name": "[permiso denegado]", "type": "file"})
    return node


# ====== API módulo financiero ======

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_tree(request):
    """Arbol de carpetas de LIBRO_BALANCE_ROOT (subidos). Params: depth, includeFiles."""
    depth = int(request.query_params.get('depth', 3))
    include_files = request.query_params.get('includeFiles', 'true').lower() != 'false'
    root = _get_balance_root()
    data = _build_tree(root, root, max_depth=max(1, min(depth, 8)), include_files=include_files)
    return Response({
        'root': root.name,
        'absolute_root': str(root),
        'tree': data.get('children', []),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_download(request):
    """Descarga un archivo bajo LIBRO_BALANCE_ROOT indicado por path relativo (?path=rel)."""
    rel = request.query_params.get('path')
    if not rel:
        return Response({"error": "Parámetro 'path' requerido"}, status=400)
    root = _get_balance_root()
    try:
        root_resolved = root.resolve(strict=False)
        target = (root / Path(rel)).resolve(strict=False)
    except Exception:
        return Response({"error": "Ruta inválida"}, status=400)

    # Evitar path traversal fuera de root
    root_prefix = str(root_resolved) + os.sep
    if not (str(target).startswith(root_prefix) or str(target) == str(root_resolved)):
        return Response({"error": "Ruta fuera de la raíz"}, status=400)
    if not target.exists() or not target.is_file():
        return Response({"error": "Archivo no encontrado"}, status=404)

    ext = target.suffix.lower()
    if ext == '.xlsx':
        ctype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif ext == '.xls':
        ctype = 'application/vnd.ms-excel'
    else:
        ctype = 'application/octet-stream'

    return FileResponse(open(target, 'rb'), as_attachment=True, filename=target.name, content_type=ctype)


@api_view(['DELETE', 'POST'])
@permission_classes([IsAuthenticated])
def finanzas_delete(request):
    """Elimina un archivo bajo LIBRO_BALANCE_ROOT indicado por path relativo (?path=rel o JSON {path})."""
    rel = request.query_params.get('path') or (request.data.get('path') if hasattr(request, 'data') else None)
    if not rel:
        return Response({"error": "Parámetro 'path' requerido"}, status=400)
    root = _get_balance_root()
    try:
        root_resolved = root.resolve(strict=False)
        target = (root / Path(rel)).resolve(strict=False)
    except Exception:
        return Response({"error": "Ruta inválida"}, status=400)

    # Evitar path traversal fuera de root
    root_prefix = str(root_resolved) + os.sep
    if not (str(target).startswith(root_prefix) or str(target) == str(root_resolved)):
        return Response({"error": "Ruta fuera de la raíz"}, status=400)
    if not target.exists():
        return Response({"error": "No existe"}, status=404)
    if target.is_dir():
        return Response({"error": "Sólo se permiten archivos, no carpetas"}, status=400)

    try:
        target.unlink()
        return Response({"success": True, "deleted": rel})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finanzas_etl_populate(request):
    """
    Pobla tablas base del ETL a partir de datos ya cargados.

    Body JSON:
      {
        "year": 2025,
        "month": 9,
        "populate_public_saldos": true,
        "populate_op_saldo": true
      }

    - Si existe staging.saldos_agencia del período, copia completa a public.saldos_agencia (upsert).
    - Si no existe staging, deriva cuentas 14/21 desde finanzas.oficinas para disparar triggers de indicadores.
    - Si populate_op_saldo=true, ejecuta finanzas.sp_apply_saldos_mes(year, month).
    """
    try:
      y = int(request.data.get('year'))
      m = int(request.data.get('month'))
    except Exception:
      return Response({'error': 'Parámetros year y month requeridos y numéricos'}, status=400)

    pop_public = str(request.data.get('populate_public_saldos', 'false')).lower() in ('1', 'true', 'yes', 'on')
    pop_op = str(request.data.get('populate_op_saldo', 'false')).lower() in ('1', 'true', 'yes', 'on')

    if not (1 <= m <= 12 and y > 0):
      return Response({'error': 'Mes o año inválido'}, status=400)

    inserted_public = 0
    applied_op = 0

    with transaction.atomic():
      with connections['default'].cursor() as cur:
        if pop_public:
          # Limpiar período en public.saldos_agencia (evita residuos)
          cur.execute("DELETE FROM public.saldos_agencia WHERE anio=%s AND mes=%s", [y, m])

          # ¿Existe staging.saldos_agencia?
          cur.execute("""
            SELECT EXISTS(
              SELECT 1 FROM information_schema.tables
              WHERE table_schema='staging' AND table_name='saldos_agencia'
            )
          """)
          has_staging = bool(cur.fetchone()[0])

          if has_staging:
            # Copia completa desde staging
            cur.execute(
              """
              INSERT INTO public.saldos_agencia
                (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
              SELECT
                sa.cuenta::text, sa.anio::int, sa.mes::int, sa.agencia_codigo::int,
                sa.saldo_inicial::numeric, sa.debito::numeric, sa.credito::numeric, sa.saldo_final::numeric
              FROM staging.saldos_agencia sa
              WHERE sa.anio=%s AND sa.mes=%s
              ON CONFLICT (cuenta, anio, mes, agencia_codigo)
              DO UPDATE SET
                saldo_inicial=EXCLUDED.saldo_inicial,
                debito=EXCLUDED.debito,
                credito=EXCLUDED.credito,
                saldo_final=EXCLUDED.saldo_final
              """,
              [y, m]
            )
            inserted_public = cur.rowcount or 0
            # Fallback: si staging existe pero no hay filas para el período, derivar 14/21 desde finanzas.oficinas
            if inserted_public == 0:
              cur.execute(
                """
                INSERT INTO public.saldos_agencia
                  (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                SELECT
                  '14', o.anio, o.mes, po.codigo, 0, 0, 0,
                  COALESCE(NULLIF(o.cta_puc_14,''),'0')::numeric
                FROM finanzas.oficinas o
                JOIN public.oficinas po ON po.id=o.oficina_id
                WHERE o.anio=%s AND o.mes=%s
                ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                """,
                [y, m]
              )
              r1 = cur.rowcount or 0
              cur.execute(
                """
                INSERT INTO public.saldos_agencia
                  (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                SELECT
                  '21', o.anio, o.mes, po.codigo, 0, 0, 0,
                  COALESCE(NULLIF(o.cta_puc_21,''),'0')::numeric
                FROM finanzas.oficinas o
                JOIN public.oficinas po ON po.id=o.oficina_id
                WHERE o.anio=%s AND o.mes=%s
                ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                """,
                [y, m]
              )
              inserted_public = r1 + (cur.rowcount or 0)
          else:
            # Fallback mínimo: 14/21 desde finanzas.oficinas
            cur.execute(
              """
              INSERT INTO public.saldos_agencia
                (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
              SELECT
                '14', o.anio, o.mes, po.codigo, 0, 0, 0,
                COALESCE(NULLIF(o.cta_puc_14,''),'0')::numeric
              FROM finanzas.oficinas o
              JOIN public.oficinas po ON po.id=o.oficina_id
              WHERE o.anio=%s AND o.mes=%s
              ON CONFLICT (cuenta, anio, mes, agencia_codigo)
              DO UPDATE SET saldo_final=EXCLUDED.saldo_final
              """,
              [y, m]
            )
            r1 = cur.rowcount or 0
            cur.execute(
              """
              INSERT INTO public.saldos_agencia
                (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
              SELECT
                '21', o.anio, o.mes, po.codigo, 0, 0, 0,
                COALESCE(NULLIF(o.cta_puc_21,''),'0')::numeric
              FROM finanzas.oficinas o
              JOIN public.oficinas po ON po.id=o.oficina_id
              WHERE o.anio=%s AND o.mes=%s
              ON CONFLICT (cuenta, anio, mes, agencia_codigo)
              DO UPDATE SET saldo_final=EXCLUDED.saldo_final
              """,
              [y, m]
            )
            inserted_public = r1 + (cur.rowcount or 0)

        if pop_op:
          # Consolidar en op_saldo_mensual desde staging/public
          cur.execute("CALL finanzas.sp_apply_saldos_mes(%s, %s);", [y, m])
          applied_op = 1

    return Response({
      'ok': True,
      'inserted': {
        'saldos_agencia': inserted_public,
        'op_saldo_mensual': applied_op,
      },
      'params': {'year': y, 'month': m}
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finanzas_upload(request):
    """Sube archivo Excel: Listado_balances_Consolidado_<Mes>_<Año>.xlsx al directorio Aanoo_<AÑO>."""
    f = request.FILES.get('file')
    if not f:
        return Response({"success": False, "error": "Archivo no encontrado (campo 'file')."}, status=400)

    m = FNAME_RE.search(f.name)
    if not m:
        return Response({
            "success": False,
            "error": "Nombre inválido. Usa: Listado_balances_Consolidado_<Mes>_<Año>.xlsx"
        }, status=400)

    mes_txt, anio_txt = m.group(1), m.group(2)
    if _norm(mes_txt) not in MESES:
        return Response({"success": False, "error": f"Mes no reconocido: {mes_txt}"}, status=400)

    anio = int(anio_txt)
    root = _get_balance_root()
    target_dir = root / f"Aanoo_{anio}"
    target_dir.mkdir(parents=True, exist_ok=True)
    dest_path = target_dir / Path(f.name).name
    if dest_path.exists():
        return Response({"success": False, "error": f"Ya existe un archivo con ese nombre en {target_dir}"}, status=400)

    with open(dest_path, "wb+") as dst:
        for chunk in f.chunks():
            dst.write(chunk)

    return Response({
        "success": True,
        "saved_name": dest_path.name,
        "anio_dir": f"Aanoo_{anio}",
        "dest_path": str(dest_path),
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_files(request):
    """Lista los archivos subidos, agrupados por año (Aanoo_YYYY)."""
    root = _get_balance_root()
    result = []
    if not root.exists():
        return Response({"files": result})
    for year_dir in sorted(root.glob('Aanoo_*')):
        if year_dir.is_dir():
            year_item = {
                'year': year_dir.name.replace('Aanoo_', ''),
                'path': str(year_dir),
                'files': [p.name for p in sorted(year_dir.glob('*.xls*'))]
            }
            result.append(year_item)
    return Response({"files": result})


@api_view(['GET'])
@permission_classes([AllowAny])
def finanzas_sample(request):
    """Datos mock para desarrollar UI financiera en React."""
    return Response({
        'menus': [
            {'key': 'carga_balance', 'label': 'Carga de Libro de Balance'},
            {'key': 'indicadores', 'label': 'Indicadores'},
            {'key': 'cupos', 'label': 'Cupos'},
        ],
        'upload': {
            'pattern': 'Listado_balances_Consolidado_<Mes>_<Año>.xlsx',
            'months_supported': list(MESES.keys()),
            'destination': 'Aanoo_<AÑO> dentro de LIBRO_BALANCE_ROOT',
        },
        'endpoints': {
            'tree': '/api/v1/finanzas/tree/',
            'upload': '/api/v1/finanzas/upload/',
            'files': '/api/v1/finanzas/files/',
            'indicadores_spec': '/api/v1/finanzas/indicadores/spec/',
            'indicadores_list': '/api/v1/finanzas/indicadores/',
            'indicadores_series': '/api/v1/finanzas/indicadores/series/',
            'cupos_spec': '/api/v1/finanzas/cupos/spec/',
            'cupos_list': '/api/v1/finanzas/cupos/',
            'cupos_credito_spec': '/api/v1/finanzas/cupos-credito/spec/',
            'cupos_credito_list': '/api/v1/finanzas/cupos-credito/',
            'presupuesto_spec': '/api/v1/finanzas/presupuesto/spec/',
            'presupuesto_list': '/api/v1/finanzas/presupuesto/',
            'indicadores_consolidados': '/api/v1/finanzas/indicadores/consolidados/',
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_indicadores_spec(request):
    spec = {
        'filters': [
            {'name': 'year', 'label': 'Año', 'type': 'integer', 'min': 2018, 'max': 2035, 'default': datetime.now().year},
            {'name': 'month', 'label': 'Mes', 'type': 'integer', 'min': 1, 'max': 12},
            {'name': 'agency', 'label': 'Agencia', 'type': 'select', 'options': [
                {'value': 'central', 'label': 'Agencia Central'},
                {'value': 'norte', 'label': 'Agencia Norte'},
                {'value': 'sur', 'label': 'Agencia Sur'},
            ]},
        ],
        'kpis': [
            {
                'id': 'cartera_total', 'name': 'Cartera Total', 'unit': 'COP', 'decimals': 0,
                'direction': 'higher_is_better', 'formula': 'SUM(saldo_cartera)', 'source': 'libro_balance'
            },
            {
                'id': 'mora', 'name': 'Mora (%)', 'unit': '%', 'decimals': 2,
                'direction': 'lower_is_better', 'formula': 'cartera_en_mora / cartera_total * 100', 'source': 'libro_balance'
            },
            {
                'id': 'liquidez', 'name': 'Índice de Liquidez', 'unit': 'ratio', 'decimals': 2,
                'direction': 'higher_is_better', 'formula': 'activos_corrientes / pasivos_corrientes', 'source': 'libro_balance'
            },
        ],
        'table': {
            'columns': [
                {'key': 'period', 'label': 'Periodo', 'type': 'string'},
                {'key': 'value', 'label': 'Valor', 'type': 'number'}
            ]
        }
    }
    return Response(spec)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_indicadores_list(request):
    year = int(request.query_params.get('year', datetime.now().year))
    month = int(request.query_params.get('month', datetime.now().month))
    agency = request.query_params.get('agency', 'central')
    data = [
        {'kpi': 'cartera_total', 'label': 'Cartera Total', 'unit': 'COP', 'value': 12500000000, 'year': year, 'month': month, 'agency': agency},
        {'kpi': 'mora', 'label': 'Mora (%)', 'unit': '%', 'value': 4.25, 'year': year, 'month': month, 'agency': agency},
        {'kpi': 'liquidez', 'label': 'Índice de Liquidez', 'unit': 'ratio', 'value': 1.23, 'year': year, 'month': month, 'agency': agency},
    ]
    return Response({'items': data, 'filters': {'year': year, 'month': month, 'agency': agency}})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_indicadores_series(request):
    kpi = request.query_params.get('kpi', 'cartera_total')
    year = int(request.query_params.get('year', datetime.now().year))
    agency = request.query_params.get('agency', 'central')
    base = {
        'cartera_total': 10000000000,
        'mora': 5.0,
        'liquidez': 1.1,
    }.get(kpi, 0)
    series = []
    for m in range(1, 13):
        if kpi == 'cartera_total':
            val = base * (1 + (m - 6) * 0.01)
        elif kpi == 'mora':
            val = max(2.5, base + (6 - m) * 0.15)
        elif kpi == 'liquidez':
            val = base + (m % 3) * 0.05
        else:
            val = base
        series.append({'month': m, 'value': round(val, 2) if isinstance(val, float) else int(val)})
    return Response({'kpi': kpi, 'year': year, 'agency': agency, 'series': series})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_cupos_spec(request):
    spec = {
        'form': [
            {'name': 'fecha', 'label': 'Fecha', 'type': 'date', 'required': True},
            {'name': 'agencia', 'label': 'Agencia', 'type': 'select', 'required': True, 'options': [
                {'value': 'central', 'label': 'Agencia Central'},
                {'value': 'norte', 'label': 'Agencia Norte'},
                {'value': 'sur', 'label': 'Agencia Sur'},
            ]},
            {'name': 'producto', 'label': 'Producto', 'type': 'select', 'required': True, 'options': [
                {'value': 'consumo', 'label': 'Consumo'},
                {'value': 'microcredito', 'label': 'Microcrédito'},
                {'value': 'comercial', 'label': 'Comercial'},
            ]},
            {'name': 'cupo_asignado', 'label': 'Cupo Asignado', 'type': 'number', 'min': 0, 'required': True},
            {'name': 'cupo_utilizado', 'label': 'Cupo Utilizado', 'type': 'number', 'min': 0, 'required': True},
            {'name': 'observaciones', 'label': 'Observaciones', 'type': 'text', 'maxLength': 500},
        ],
        'constraints': [
            {'rule': 'cupo_utilizado <= cupo_asignado', 'message': 'El cupo utilizado no puede superar el asignado'},
            {'rule': 'cupo_asignado >= 0 and cupo_utilizado >= 0', 'message': 'Valores no pueden ser negativos'},
        ],
        'table': {
            'columns': [
                {'key': 'fecha', 'label': 'Fecha'},
                {'key': 'agencia', 'label': 'Agencia'},
                {'key': 'producto', 'label': 'Producto'},
                {'key': 'cupo_asignado', 'label': 'Cupo Asignado', 'type': 'number'},
                {'key': 'cupo_utilizado', 'label': 'Utilizado', 'type': 'number'},
                {'key': 'cupo_disponible', 'label': 'Disponible', 'type': 'number'},
                {'key': 'observaciones', 'label': 'Observaciones'},
            ]
        }
    }
    return Response(spec)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def finanzas_cupos(request):
    if request.method == 'GET':
        items = [
            {
                'fecha': '2025-08-01', 'agencia': 'central', 'producto': 'consumo',
                'cupo_asignado': 1200000000, 'cupo_utilizado': 450000000,
                'cupo_disponible': 750000000, 'observaciones': 'Campaña mitad de año'
            },
            {
                'fecha': '2025-08-01', 'agencia': 'norte', 'producto': 'microcredito',
                'cupo_asignado': 600000000, 'cupo_utilizado': 420000000,
                'cupo_disponible': 180000000, 'observaciones': ''
            },
        ]
        return Response({'items': items})

    payload = request.data.copy()
    try:
        asignado = float(payload.get('cupo_asignado', 0))
        utilizado = float(payload.get('cupo_utilizado', 0))
    except ValueError:
        return Response({'error': 'Valores numéricos inválidos'}, status=400)

    if asignado < 0 or utilizado < 0:
        return Response({'error': 'Valores no pueden ser negativos'}, status=400)
    if utilizado > asignado:
        return Response({'error': 'El cupo utilizado no puede superar el asignado'}, status=400)

    disponible = asignado - utilizado
    created = {
        'fecha': payload.get('fecha') or datetime.now().strftime('%Y-%m-%d'),
        'agencia': payload.get('agencia', 'central'),
        'producto': payload.get('producto', 'consumo'),
        'cupo_asignado': asignado,
        'cupo_utilizado': utilizado,
        'cupo_disponible': disponible,
        'observaciones': payload.get('observaciones', ''),
        'created_at': datetime.now().isoformat(timespec='seconds')
    }
    return Response(created, status=201)


# ====== Cupos de Crédito ======

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_cupos_credito_spec(request):
    """Esquema de la Tabla 2: Cupos de Crédito."""
    spec = {
        'columns': [
            {'key': 'fecha_renovado', 'label': 'Fecha Renovado', 'type': 'string'},
            {'key': 'cuenta', 'label': 'Cuenta (Id_cuenta)', 'type': 'string'},
            {'key': 'entidad_financiera', 'label': 'Entidad Financiera', 'type': 'string'},
            {'key': 'cupo_asignado', 'label': 'Cupo Asignado', 'type': 'number'},
            {'key': 'cupo_ejecutado', 'label': 'Cupo Ejecutado', 'type': 'number'},
            {'key': 'disponible', 'label': 'Disponible', 'type': 'number'},
            {'key': 'garantia', 'label': 'Garantía', 'type': 'string'},
            {'key': 'porcentaje_utilizacion', 'label': '% Utilización', 'type': 'number'},
            {'key': 'plazo', 'label': 'Plazo', 'type': 'string'},
        ]
    }
    return Response(spec)


@api_view(['GET'])
@permission_classes([IsAuthenticated])

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def finanzas_cupos_credito_list(request):
    """Cupos de Crédito desde tablas del esquema finanzas (tabla: finanzas.cupos_bancarios).

    GET filtros opcionales: ?year=YYYY&month=M&entidad=...&limit=100
    POST: inserta/actualiza registro. Si se envía id, hace UPDATE; si no, INSERT.
    """
    if request.method == 'POST':
        data = request.data
        rec_id = data.get('id')
        entidad = (data.get('entidad_financiera') or data.get('entidad') or '').strip()
        cuenta = (data.get('cuenta') or data.get('cuentas_balance') or '').strip()
        fecha = (data.get('fecha_renovado') or '').strip()
        def to_float(x):
            try:
                return None if x in (None, '', '-') else float(x)
            except Exception:
                return None
        cupo_asignado = to_float(data.get('cupo_asignado'))
        cupo_ejecutado = to_float(data.get('cupo_ejecutado'))
        garantia = (data.get('garantia') or '').strip() or None
        plazo_meses = data.get('plazo_meses') or data.get('plazo')
        try:
            plazo_meses = int(str(plazo_meses).split()[0]) if plazo_meses not in (None, '') else None
        except Exception:
            plazo_meses = None
        tasa_pct = to_float(data.get('tasa') or data.get('tasa_pct'))

        if not (entidad and fecha and cupo_asignado is not None):
            return Response({'error': 'entidad_financiera, fecha_renovado y cupo_asignado son obligatorios'}, status=400)

        disponible = None
        utilizacion_pct = None
        if cupo_asignado is not None and cupo_ejecutado is not None:
            disponible = cupo_asignado - cupo_ejecutado
            try:
                utilizacion_pct = (cupo_ejecutado / cupo_asignado) * 100 if cupo_asignado else 0
            except Exception:
                utilizacion_pct = None

        from django.db import connections
        with connections['default'].cursor() as c:
            if rec_id:
                c.execute(
                    """
                    UPDATE finanzas.cupos_bancarios
                    SET entidad_financiera=%s, cuentas_balance=%s, fecha_renovado=%s,
                        cupo_asignado=%s, cupo_ejecutado=%s, disponible=COALESCE(%s, cupo_asignado - COALESCE(cupo_ejecutado,0)),
                        garantia=%s, utilizacion_pct=%s, plazo_meses=%s, tasa_pct=%s
                    WHERE id=%s
                    """,
                    [entidad, cuenta or None, fecha, cupo_asignado, cupo_ejecutado, disponible, garantia, utilizacion_pct, plazo_meses, tasa_pct, rec_id]
                )
                return Response({'success': True, 'updated_id': rec_id})
            else:
                c.execute(
                    """
                    INSERT INTO finanzas.cupos_bancarios
                        (entidad_financiera, cuentas_balance, fecha_renovado, cupo_asignado,
                         cupo_ejecutado, disponible, garantia, utilizacion_pct, plazo_meses, tasa_pct, created_at)
                    VALUES (%s,%s,%s,%s,%s,COALESCE(%s, %s - COALESCE(%s,0)),%s,%s,%s,%s, NOW())
                    RETURNING id
                    """,
                    [entidad, cuenta or None, fecha, cupo_asignado, cupo_ejecutado, disponible, cupo_asignado, cupo_ejecutado, garantia, utilizacion_pct, plazo_meses, tasa_pct]
                )
                new_id = c.fetchone()[0]
                return Response({'success': True, 'id': new_id}, status=201)

    # GET
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    entidad = request.query_params.get('entidad')
    limit = int(request.query_params.get('limit', '200'))
    where = []
    # Expresiones robustas para convertir mes/anio a entero sin lanzar errores
    month_expr = CASE_MONTH_TO_INT
    year_expr = CASE_YEAR_TO_INT
    params = {}
    if year:
        where.append('EXTRACT(year FROM fecha_renovado) = %(year)s::int')
        params['year'] = year
    if month:
        where.append('EXTRACT(month FROM fecha_renovado) = %(month)s::int')
        params['month'] = month
    if entidad:
        where.append('entidad_financiera ILIKE %(entidad)s')
        params['entidad'] = f'%{entidad}%'
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    sql = f"""
        SELECT 
            fecha_renovado::text AS fecha_renovado,
            cuentas_balance::text AS cuenta,
            entidad_financiera::text AS entidad_financiera,
            cupo_asignado::numeric AS cupo_asignado,
            cupo_ejecutado::numeric AS cupo_ejecutado,
            disponible::numeric AS disponible,
            garantia::text AS garantia,
            utilizacion_pct::numeric AS porcentaje_utilizacion,
            COALESCE(plazo_meses::text || ' meses', NULL) AS plazo,
            tasa_pct::numeric AS tasa
        FROM finanzas.cupos_bancarios
        {where_sql}
        ORDER BY fecha_renovado DESC NULLS LAST, entidad_financiera, cuentas_balance
        LIMIT {limit}
    """
    from django.db import connections
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({'source': 'finanzas.cupos_bancarios', 'count': len(items), 'items': items, 'filters': {'year': year, 'month': month, 'entidad': entidad}})
    except Exception as e:
        return Response({'error': str(e), 'source': 'finanzas.cupos_bancarios'}, status=400)


class CuposCreditoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Lee Cupos de Crédito desde finanzas.resumen_mensual_bancos.
        Mapea a los campos esperados por el frontend.
        """
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        entidad = request.query_params.get('entidad')
        rec_id = request.query_params.get('id')
        limit = int(request.query_params.get('limit', '200'))

        # ID sintético, estable y dentro del rango seguro de JS (<= 9e15)
        # Tomamos 64 bits del md5 y aplicamos abs() % 9.007e15 aprox
        ID_EXPR = "(abs((('x'||substr(md5(banco || ':' || anio::text || ':' || mes::text),1,16))::bit(64)::bigint)) % 9007199250000000)"

        where = []
        params = {}
        if year:
            where.append('anio = %(year)s::int')
            params['year'] = year
        if month:
            where.append('mes = %(month)s::int')
            params['month'] = month
        if entidad:
            where.append('banco ILIKE %(entidad)s')
            params['entidad'] = f'%{entidad}%'
        if rec_id:
            where.append(f"{ID_EXPR} = %(id)s::bigint")
            params['id'] = rec_id
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

        sql = f"""
            WITH base AS (
                SELECT 
                    {ID_EXPR} AS id,
                    anio,
                    mes,
                    banco::text AS entidad_financiera,
                    cupo_asignado::numeric AS cupo_asignado,
                    saldo_total_mes::numeric AS cupo_ejecutado,
                    porcentaje_utilizado::numeric AS porcentaje_utilizacion
                FROM finanzas.resumen_mensual_bancos
                {where_sql}
            )
            SELECT
                b.id,
                to_char(make_date(b.anio, b.mes, 1), 'YYYY-MM-DD') AS fecha_renovado,
                COALESCE(
                    (
                        SELECT string_agg(DISTINCT c.cuenta, ', ' ORDER BY c.cuenta)
                        FROM finanzas.cupos_credito c
                        WHERE upper(c.entidad_financiera) = upper(b.entidad_financiera)
                    ),
                    'Sin Especificar'
                ) AS cuenta,
                b.entidad_financiera,
                b.cupo_asignado,
                b.cupo_ejecutado,
                GREATEST((b.cupo_asignado - b.cupo_ejecutado), 0)::numeric AS disponible,
                NULL::text AS garantia,
                b.porcentaje_utilizacion,
                NULL::text AS plazo,
                NULL::text AS tasa
            FROM base b
            ORDER BY b.anio DESC, b.mes DESC, b.entidad_financiera
            LIMIT {limit}
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, sql, params)
                cols = [col[0] for col in c.description]
                items = [dict(zip(cols, row)) for row in c.fetchall()]
            return Response({'source': 'finanzas.resumen_mensual_bancos', 'count': len(items), 'items': items, 'filters': {'year': year, 'month': month, 'entidad': entidad}})
        except Exception as e:
            return Response({'error': str(e), 'source': 'finanzas.resumen_mensual_bancos'}, status=400)

    def post(self, request):
        """
        Inserta/actualiza en finanzas.resumen_mensual_bancos.
        - banco  <= entidad_financiera
        - anio/mes <= de fecha_renovado (o de year/month si vienen en query)
        - cupo_asignado <= cupo_asignado
        - saldo_total_mes <= cupo_ejecutado
        - porcentaje_utilizado se calcula si no se envía
        Ignora: cuenta, garantia, plazo, tasa
        """
        data = request.data
        entidad = (data.get('entidad_financiera') or data.get('entidad') or '').strip()
        fecha_in = _to_iso_date((data.get('fecha_renovado') or '').strip())

        def to_float(x):
            try:
                return None if x in (None, '', '-') else float(x)
            except Exception:
                return None

        cupo_asignado = to_float(data.get('cupo_asignado'))
        cupo_ejecutado = to_float(data.get('cupo_ejecutado'))

        # Permitir year/month por query si no viene fecha
        if not fecha_in:
            y = request.query_params.get('year')
            m = request.query_params.get('month')
            try:
                if y and m:
                    fecha_in = f"{int(y):04d}-{int(m):02d}-01"
            except Exception:
                fecha_in = None

        if not (entidad and fecha_in and cupo_asignado is not None and cupo_ejecutado is not None):
            return Response({'error': 'entidad_financiera, fecha_renovado, cupo_asignado y cupo_ejecutado son obligatorios'}, status=400)

        try:
            y, m, _ = [int(p) for p in fecha_in.split('-')]
        except Exception:
            return Response({'error': 'fecha_renovado inválida, use DD/MM/YYYY o YYYY-MM-DD'}, status=400)

        try:
            porc = (cupo_ejecutado / cupo_asignado * 100.0) if cupo_asignado else 0.0
        except Exception:
            porc = None

        with connections['default'].cursor() as c:
            c.execute(
                """
                INSERT INTO finanzas.resumen_mensual_bancos
                    (banco, anio, mes, cupo_asignado, saldo_total_mes, porcentaje_utilizado, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (banco, anio, mes)
                DO UPDATE SET
                    cupo_asignado = EXCLUDED.cupo_asignado,
                    saldo_total_mes = EXCLUDED.saldo_total_mes,
                    porcentaje_utilizado = EXCLUDED.porcentaje_utilizado,
                    updated_at = NOW()
                RETURNING banco, anio, mes
                """,
                [entidad, y, m, cupo_asignado, cupo_ejecutado, porc]
            )
            banco, anio, mes = c.fetchone()

        # Construir id sintético igual al de GET
        with connections['default'].cursor() as c:
            c.execute(
                """
                SELECT (abs((('x'||substr(md5(%s || ':' || %s::text || ':' || %s::text),1,16))::bit(64)::bigint)) % 9007199250000000)
                """,
                [banco, anio, mes]
            )
            new_id = c.fetchone()[0]

        return Response({'success': True, 'id': new_id}, status=201)

    def delete(self, request):
        """Elimina por id sintético o por (entidad, year, month) si vienen explícitos."""
        rec_id = request.query_params.get('id')
        entidad = request.query_params.get('entidad')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        try:
            with connections['default'].cursor() as c:
                if rec_id:
                    c.execute(
                        """
                        DELETE FROM finanzas.resumen_mensual_bancos
                        WHERE (abs((('x'||substr(md5(banco || ':' || anio::text || ':' || mes::text),1,16))::bit(64)::bigint)) % 9007199250000000) = %s
                        """,
                        [rec_id]
                    )
                elif entidad and year and month:
                    c.execute(
                        """
                        DELETE FROM finanzas.resumen_mensual_bancos
                        WHERE banco=%s AND anio=%s::int AND mes=%s::int
                        """,
                        [entidad, year, month]
                    )
                else:
                    return Response({'error': 'Proporcione id o (entidad, year, month) para eliminar'}, status=400)

                if c.rowcount == 0:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                return Response({'success': True, 'deleted_id': rec_id or f"{entidad}:{year}:{month}"})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ====== Crédito: Radicaciones (solo lectura) ======

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def credito_radicaciones(request):
    """
    Devuelve radicaciones de crédito agregadas por mes desde credito.kpi_radicaciones.
    Permite filtrar por año/mes y limitar la cantidad de filas.
    POST: inserta una nueva fila básica.
    """
    if request.method == 'POST':
        payload = request.data or {}
        periodo = (payload.get('periodo') or '').strip()
        oficina_id = payload.get('oficina_id')
        if not periodo:
            return Response({'error': 'periodo es obligatorio (YYYY-MM)'}, status=400)
        if oficina_id is None or str(oficina_id).strip() == "":
            return Response({'error': 'oficina_id es obligatorio'}, status=400)
        try:
            periodo_ini = datetime.strptime(f"{periodo}-01", "%Y-%m-%d").date()
        except Exception:
            return Response({'error': 'periodo debe tener formato YYYY-MM'}, status=400)
        periodo_fin = (periodo_ini.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        anio = periodo_ini.year
        mes = periodo_ini.month
        fecha_corte = payload.get('fecha_corte') or periodo_fin
        campos = {
            'radicados_valor': payload.get('radicados_valor'),
            'radicados_cantidad': payload.get('radicados_cantidad'),
            'radicados_pct': payload.get('radicados_pct'),
            'aprobados_valor': payload.get('aprobados_valor'),
            'aprobados_cantidad': payload.get('aprobados_cantidad'),
            'aprobados_pct': payload.get('aprobados_pct'),
            'negados_valor': payload.get('negados_valor'),
            'negados_cantidad': payload.get('negados_cantidad'),
            'negados_pct': payload.get('negados_pct'),
            'aplazados_valor': payload.get('aplazados_valor'),
            'aplazados_cantidad': payload.get('aplazados_cantidad'),
            'aplazados_pct': payload.get('aplazados_pct'),
            'sin_decision_valor': payload.get('sin_decision_valor'),
            'sin_decision_cantidad': payload.get('sin_decision_cantidad'),
            'sin_decision_pct': payload.get('sin_decision_pct'),
        }
        insert_sql = """
            INSERT INTO credito.kpi_radicaciones (
              periodo_ini, periodo_fin, oficina_id, anio, mes, fecha_corte,
              rad_valor, rad_cantidad, rad_pct,
              apr_valor, apr_cantidad, apr_pct,
              neg_valor, neg_cantidad, neg_pct,
              apl_valor, apl_cantidad, apl_pct,
              sde_valor, sde_cantidad, sde_pct,
              total_valor_periodo, total_cant_periodo
            )
            VALUES (
              %(periodo_ini)s::date, %(periodo_fin)s::date, %(oficina_id)s::bigint, %(anio)s, %(mes)s, %(fecha_corte)s::date,
              %(radicados_valor)s, %(radicados_cantidad)s, %(radicados_pct)s,
              %(aprobados_valor)s, %(aprobados_cantidad)s, %(aprobados_pct)s,
              %(negados_valor)s, %(negados_cantidad)s, %(negados_pct)s,
              %(aplazados_valor)s, %(aplazados_cantidad)s, %(aplazados_pct)s,
              %(sin_decision_valor)s, %(sin_decision_cantidad)s, %(sin_decision_pct)s,
              COALESCE(%(radicados_valor)s,0)+COALESCE(%(aprobados_valor)s,0)+COALESCE(%(negados_valor)s,0)+COALESCE(%(aplazados_valor)s,0)+COALESCE(%(sin_decision_valor)s,0),
              COALESCE(%(radicados_cantidad)s,0)+COALESCE(%(aprobados_cantidad)s,0)+COALESCE(%(negados_cantidad)s,0)+COALESCE(%(aplazados_cantidad)s,0)+COALESCE(%(sin_decision_cantidad)s,0)
            )
            RETURNING id
        """
        params = {
            'periodo_ini': periodo_ini,
            'periodo_fin': periodo_fin,
            'oficina_id': oficina_id,
            'anio': anio,
            'mes': mes,
            'fecha_corte': fecha_corte,
            **campos,
        }
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, params)
                new_id = c.fetchone()[0]
            return Response({'id': new_id, 'periodo': periodo, 'oficina_id': oficina_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando credito.kpi_radicaciones")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    try:
        limit = int(request.query_params.get('limit', '200'))
    except Exception:
        limit = 200
    limit = max(1, min(limit, 2000))

    where = []
    params = {}
    if year:
        try:
            params['year'] = int(year)
            where.append("anio_calc = %(year)s")
        except Exception:
            return Response({'error': 'El año debe ser numérico'}, status=400)
    if month:
        try:
            params['month'] = int(month)
            where.append("mes_calc = %(month)s")
        except Exception:
            return Response({'error': 'El mes debe ser numérico'}, status=400)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ''

    sql = f"""
        WITH base AS (
            SELECT
                date_trunc('month', kr.periodo_ini)::date AS periodo,
                COALESCE(MAX(kr.periodo_fin), date_trunc('month', kr.periodo_ini) + INTERVAL '1 month - 1 day')::date AS periodo_fin,
                COALESCE(MAX(kr.fecha_corte), date_trunc('month', kr.periodo_ini))::date AS fecha_corte,
                SUM(COALESCE(kr.rad_valor, 0)) AS rad_valor,
                SUM(COALESCE(kr.rad_cantidad, 0)) AS rad_cantidad,
                SUM(COALESCE(kr.apr_valor, 0)) AS apr_valor,
                SUM(COALESCE(kr.apr_cantidad, 0)) AS apr_cantidad,
                SUM(COALESCE(kr.neg_valor, 0)) AS neg_valor,
                SUM(COALESCE(kr.neg_cantidad, 0)) AS neg_cantidad,
                SUM(COALESCE(kr.apl_valor, 0)) AS apl_valor,
                SUM(COALESCE(kr.apl_cantidad, 0)) AS apl_cantidad,
                SUM(COALESCE(kr.sde_valor, 0)) AS sde_valor,
                SUM(COALESCE(kr.sde_cantidad, 0)) AS sde_cantidad,
                SUM(COALESCE(kr.total_valor_periodo, 0)) AS total_valor,
                SUM(COALESCE(kr.total_cant_periodo, 0)) AS total_cantidad
            FROM credito.kpi_radicaciones kr
            GROUP BY date_trunc('month', kr.periodo_ini)
        )
        SELECT
            to_char(periodo, 'YYYY-MM') AS periodo,
            EXTRACT(YEAR FROM periodo)::int AS anio,
            EXTRACT(MONTH FROM periodo)::int AS mes,
            periodo AS periodo_ini,
            periodo_fin,
            fecha_corte,
            rad_valor,
            rad_cantidad,
            CASE WHEN NULLIF(total_cantidad, 0) IS NOT NULL THEN ROUND(rad_cantidad::numeric * 100 / NULLIF(total_cantidad, 0), 2) END AS rad_pct,
            apr_valor,
            apr_cantidad,
            CASE WHEN NULLIF(total_cantidad, 0) IS NOT NULL THEN ROUND(apr_cantidad::numeric * 100 / NULLIF(total_cantidad, 0), 2) END AS apr_pct,
            neg_valor,
            neg_cantidad,
            CASE WHEN NULLIF(total_cantidad, 0) IS NOT NULL THEN ROUND(neg_cantidad::numeric * 100 / NULLIF(total_cantidad, 0), 2) END AS neg_pct,
            apl_valor,
            apl_cantidad,
            CASE WHEN NULLIF(total_cantidad, 0) IS NOT NULL THEN ROUND(apl_cantidad::numeric * 100 / NULLIF(total_cantidad, 0), 2) END AS apl_pct,
            sde_valor,
            sde_cantidad,
            CASE WHEN NULLIF(total_cantidad, 0) IS NOT NULL THEN ROUND(sde_cantidad::numeric * 100 / NULLIF(total_cantidad, 0), 2) END AS sde_pct,
            total_valor AS total_valor_periodo,
            total_cantidad AS total_cant_periodo
        FROM base
        {where_sql}
        ORDER BY periodo DESC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'credito.kpi_radicaciones',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo credito.kpi_radicaciones")
        return Response({'error': str(exc)}, status=500)


# ====== Crédito: Seguimiento de campañas x oficina (solo lectura) ======

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def credito_campanias_oficina(request):
    """
    Lee credito.kpi_campanias_oficina.
    Permite filtrar por anio, mes (de fecha_corte), campana_codigo y oficina_id.
    POST: inserta un registro básico.
    """
    if request.method == 'POST':
        payload = request.data or {}
        campana = (payload.get('campana') or payload.get('campana_codigo') or '').strip()
        oficina = payload.get('oficina_id')
        anio = payload.get('anio') or payload.get('year')
        fecha_corte = payload.get('fecha_corte') or payload.get('fechaCorte')
        if not anio and fecha_corte:
            try:
                anio = str(fecha_corte).split("-")[0]
            except Exception:
                anio = None
        if not campana or oficina is None or not fecha_corte or not anio:
            return Response({'error': 'campana, oficina_id, anio y fecha_corte son obligatorios'}, status=400)
        insert_sql = """
            INSERT INTO credito.kpi_campanias_oficina (
              anio,
              campana_codigo, campania_label, segmento, oficina_id, total_valor, total_cantidad,
              cch_valor, cch_cantidad, c_viv_valor, c_viv_cantidad,
              c_tc_valor, c_tc_cantidad, c_libcigg_valor, c_libcigg_cantidad,
              c_monto_valor, c_monto_cantidad, c_ccart_valor, c_ccart_cantidad,
              fng_emp255_valor, fng_emp255_cantidad, fng_emp285_valor, fng_emp285_cantidad,
              fecha_corte
            )
            VALUES (
              %(anio)s,
              %(campana)s, %(campana_label)s, %(segmento)s, %(oficina_id)s, %(total_valor)s, %(total_cantidad)s,
              %(cch_valor)s, %(cch_cantidad)s, %(c_viv_valor)s, %(c_viv_cantidad)s,
              %(c_tc_valor)s, %(c_tc_cantidad)s, %(c_libcigg_valor)s, %(c_libcigg_cantidad)s,
              %(c_monto_valor)s, %(c_monto_cantidad)s, %(c_ccart_valor)s, %(c_ccart_cantidad)s,
              %(fng_emp255_valor)s, %(fng_emp255_cantidad)s, %(fng_emp285_valor)s, %(fng_emp285_cantidad)s,
              %(fecha_corte)s::date
            )
            RETURNING id
        """
        params = {
            'anio': anio,
            'campana': campana,
            'campana_label': payload.get('campana_label'),
            'segmento': payload.get('segmento'),
            'oficina_id': payload.get('oficina_id'),
            'total_valor': payload.get('total_valor'),
            'total_cantidad': payload.get('total_cantidad'),
            'cch_valor': payload.get('cch_valor'),
            'cch_cantidad': payload.get('cch_cantidad'),
            'c_viv_valor': payload.get('c_viv_valor'),
            'c_viv_cantidad': payload.get('c_viv_cantidad'),
            'c_tc_valor': payload.get('c_tc_valor'),
            'c_tc_cantidad': payload.get('c_tc_cantidad'),
            'c_libcigg_valor': payload.get('c_libcigg_valor'),
            'c_libcigg_cantidad': payload.get('c_libcigg_cantidad'),
            'c_monto_valor': payload.get('c_monto_valor'),
            'c_monto_cantidad': payload.get('c_monto_cantidad'),
            'c_ccart_valor': payload.get('c_ccart_valor'),
            'c_ccart_cantidad': payload.get('c_ccart_cantidad'),
            'fng_emp255_valor': payload.get('fng_emp255_valor'),
            'fng_emp255_cantidad': payload.get('fng_emp255_cantidad'),
            'fng_emp285_valor': payload.get('fng_emp285_valor'),
            'fng_emp285_cantidad': payload.get('fng_emp285_cantidad'),
            'fecha_corte': fecha_corte,
        }
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, params)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando credito.kpi_campanias_oficina")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    campana = request.query_params.get('campana') or request.query_params.get('campana_codigo')
    oficina = request.query_params.get('oficina_id')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM kc.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM kc.fecha_corte) = %(month)s::int")
        params['month'] = month
    if campana:
        where.append("kc.campana_codigo ILIKE %(campana)s")
        params['campana'] = f"%{campana}%"
    if oficina:
        where.append("kc.oficina_id = %(oficina)s::bigint")
        params['oficina'] = oficina
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            kc.id,
            kc.anio,
            kc.campana_codigo,
            kc.campania_label,
            kc.segmento,
            kc.oficina_id,
            kc.total_valor,
            kc.total_cantidad,
            kc.cch_valor,
            kc.cch_cantidad,
            kc.c_viv_valor,
            kc.c_viv_cantidad,
            kc.c_tc_valor,
            kc.c_tc_cantidad,
            kc.c_libcigg_valor,
            kc.c_libcigg_cantidad,
            kc.c_monto_valor,
            kc.c_monto_cantidad,
            kc.c_ccart_valor,
            kc.c_ccart_cantidad,
            kc.fng_emp255_valor,
            kc.fng_emp255_cantidad,
            kc.fng_emp285_valor,
            kc.fng_emp285_cantidad,
            kc.fecha_corte
        FROM credito.kpi_campanias_oficina kc
        {where_sql}
        ORDER BY kc.fecha_corte DESC NULLS LAST, kc.campana_codigo, kc.oficina_id
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'credito.kpi_campanias_oficina',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'campana': campana, 'oficina': oficina, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo credito.kpi_campanias_oficina")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def credito_campanias(request):
    """
    Lee credito.kpi_campanias.
    Filtros opcionales: year/mes (fecha_corte), campana_codigo, oficina_id.
    POST: inserta registro.
    """
    if request.method == 'POST':
        payload = request.data or {}
        campana = (payload.get('campana') or payload.get('campana_codigo') or '').strip()
        oficina = payload.get('oficina_id')
        anio = payload.get('anio') or payload.get('year')
        fecha_corte = payload.get('fecha_corte') or payload.get('fechaCorte')
        if not campana or oficina is None or not anio or not fecha_corte:
            return Response({'error': 'campana, oficina_id, anio y fecha_corte son obligatorios'}, status=400)
        insert_sql = """
            INSERT INTO credito.kpi_campanias (
              campana_codigo, oficina_id, anio, valor_desembolsos, n_operaciones,
              recursos_programados, recursos_disponibles, pct_avance, estado,
              color_hex, gap_meta_valor, gap_meta_pct, codigo_op, fecha_corte
            )
            VALUES (
              %(campana)s, %(oficina_id)s, %(anio)s, %(valor_desembolsos)s, %(n_operaciones)s,
              %(recursos_programados)s, %(recursos_disponibles)s, %(pct_avance)s, %(estado)s,
              %(color_hex)s, %(gap_meta_valor)s, %(gap_meta_pct)s, %(codigo_op)s, %(fecha_corte)s::date
            )
            RETURNING id
        """
        params = {
            'campana': campana,
            'oficina_id': oficina,
            'anio': anio,
            'valor_desembolsos': payload.get('valor_desembolsos'),
            'n_operaciones': payload.get('n_operaciones'),
            'recursos_programados': payload.get('recursos_programados'),
            'recursos_disponibles': payload.get('recursos_disponibles'),
            'pct_avance': payload.get('pct_avance'),
            'estado': payload.get('estado'),
            'color_hex': payload.get('color_hex'),
            'gap_meta_valor': payload.get('gap_meta_valor'),
            'gap_meta_pct': payload.get('gap_meta_pct'),
            'codigo_op': payload.get('codigo_op'),
            'fecha_corte': fecha_corte,
        }
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, params)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando credito.kpi_campanias")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    campana = request.query_params.get('campana') or request.query_params.get('campana_codigo')
    oficina = request.query_params.get('oficina_id')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM kc.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM kc.fecha_corte) = %(month)s::int")
        params['month'] = month
    if campana:
        where.append("kc.campana_codigo ILIKE %(campana)s")
        params['campana'] = f"%{campana}%"
    if oficina:
        where.append("kc.oficina_id = %(oficina)s::int")
        params['oficina'] = oficina
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            kc.id,
            kc.anio,
            kc.campana_codigo,
            kc.n_operaciones,
            kc.valor_desembolsos,
            kc.recursos_programados,
            kc.recursos_disponibles,
            kc.pct_avance,
            kc.estado,
            kc.color_hex,
            kc.gap_meta_valor,
            kc.gap_meta_pct,
            kc.oficina_id,
            kc.codigo_op,
            kc.fecha_corte
        FROM credito.kpi_campanias kc
        {where_sql}
        ORDER BY kc.fecha_corte DESC NULLS LAST, kc.campana_codigo, kc.oficina_id
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'credito.kpi_campanias',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'campana': campana, 'oficina': oficina, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo credito.kpi_campanias")
        return Response({'error': str(exc)}, status=500)


# ====== Cartera: Asignación de llamadas (solo lectura) ======

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cartera_asignacion_llamadas(request):
    """
    Lee cartera.stg_llamadas_detalle con filtros simples.
    Filtros opcionales: year/mes (fecha_corte), gestor, estado, search (nombre/identificación/crédito/agencia).
    POST: inserta una fila básica (campos mínimos: agencia, numero_credito_raw, linea_credito, numero_identificacion, nombre_asociado).
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['agencia', 'numero_credito_raw', 'linea_credito', 'numero_identificacion', 'nombre_asociado']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO cartera.stg_llamadas_detalle (
              agencia, numero_credito_raw, linea_credito, numero_identificacion, nombre_asociado,
              saldo_capital_raw, dias_mora_raw, periodicidad_capital, tipo_garantia, celular,
              estado, gestor, fecha_gestion_raw, fecha_acuerdo_raw, gestion_titular, gestion_codeudor,
              novedad_gestion, programar_visita, gestor_apoya, calificacion, fecha_corte
            )
            VALUES (
              %(agencia)s, %(numero_credito_raw)s, %(linea_credito)s, %(numero_identificacion)s, %(nombre_asociado)s,
              %(saldo_capital_raw)s, %(dias_mora_raw)s, %(periodicidad_capital)s, %(tipo_garantia)s, %(celular)s,
              %(estado)s, %(gestor)s, %(fecha_gestion_raw)s, %(fecha_acuerdo_raw)s, %(gestion_titular)s, %(gestion_codeudor)s,
              %(novedad_gestion)s, %(programar_visita)s, %(gestor_apoya)s, %(calificacion)s, %(fecha_corte)s
            )
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_llamadas_detalle")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    gestor = request.query_params.get('gestor')
    estado = request.query_params.get('estado')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM ld.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM ld.fecha_corte) = %(month)s::int")
        params['month'] = month
    if gestor:
        where.append("ld.gestor ILIKE %(gestor)s")
        params['gestor'] = f"%{gestor}%"
    if estado:
        where.append("ld.estado ILIKE %(estado)s")
        params['estado'] = f"%{estado}%"
    if search:
        where.append("""
            (
              ld.nombre_asociado ILIKE %(search)s OR
              ld.numero_identificacion ILIKE %(search)s OR
              ld.numero_credito_raw ILIKE %(search)s OR
              ld.agencia ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            ld.id,
            ld.agencia,
            ld.numero_credito_raw AS numero_credito,
            ld.linea_credito,
            ld.numero_identificacion,
            ld.nombre_asociado,
            ld.saldo_capital_raw,
            ld.dias_mora_raw,
            ld.periodicidad_capital,
            ld.tipo_garantia,
            ld.celular,
            ld.estado,
            ld.gestor,
            ld.fecha_gestion_raw,
            ld.fecha_acuerdo_raw,
            ld.gestion_titular,
            ld.gestion_codeudor,
            ld.novedad_gestion,
            ld.programar_visita,
            ld.gestor_apoya,
            ld.calificacion,
            ld.fecha_corte
        FROM cartera.stg_llamadas_detalle ld
        {where_sql}
        ORDER BY ld.fecha_corte DESC NULLS LAST, ld.agencia, ld.nombre_asociado
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_llamadas_detalle',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'gestor': gestor, 'estado': estado, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_llamadas_detalle")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cartera_gestion_llamadas(request):
    """
    Lee cartera.stg_asignacion_llamadas.
    Filtros opcionales: year/mes (fecha_corte), oficina, gestor.
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['fecha_corte', 'oficina', 'gestor', 'llamadas_asignadas', 'obligaciones_al_dia_llamadas']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        fecha_corte = _to_iso_date(p.get('fecha_corte'))
        insert_sql = """
            INSERT INTO cartera.stg_asignacion_llamadas (
              fecha_corte, oficina, gestor, llamadas_asignadas, obligaciones_al_dia_llamadas
            )
            VALUES (%(fecha_corte)s, %(oficina)s, %(gestor)s, %(llamadas_asignadas)s, %(obligaciones_al_dia_llamadas)s)
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, {
                    'fecha_corte': fecha_corte,
                    'oficina': p.get('oficina'),
                    'gestor': p.get('gestor'),
                    'llamadas_asignadas': p.get('llamadas_asignadas'),
                    'obligaciones_al_dia_llamadas': p.get('obligaciones_al_dia_llamadas'),
                })
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_asignacion_llamadas")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    oficina = request.query_params.get('oficina')
    gestor = request.query_params.get('gestor')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM g.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM g.fecha_corte) = %(month)s::int")
        params['month'] = month
    if oficina:
        where.append("g.oficina ILIKE %(oficina)s")
        params['oficina'] = f"%{oficina}%"
    if gestor:
        where.append("g.gestor ILIKE %(gestor)s")
        params['gestor'] = f"%{gestor}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            g.id,
            g.fecha_corte,
            g.oficina,
            g.gestor,
            g.llamadas_asignadas,
            g.obligaciones_al_dia_llamadas,
            g.created_at
        FROM cartera.stg_asignacion_llamadas g
        {where_sql}
        ORDER BY g.fecha_corte DESC NULLS LAST, g.oficina
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_asignacion_llamadas',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'oficina': oficina, 'gestor': gestor, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_asignacion_llamadas")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cartera_link_llamadas(request):
    """
    Lee cartera.stg_llamadas_detalle (link de llamadas).
    Filtros opcionales: year/mes (fecha_corte), gestor, agencia, search.
    POST: inserta fila básica (usa la misma tabla que asignación de llamadas).
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['agencia', 'numero_credito_raw', 'linea_credito', 'numero_identificacion', 'nombre_asociado']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO cartera.stg_llamadas_detalle (
              agencia, numero_credito_raw, linea_credito, numero_identificacion, nombre_asociado,
              saldo_capital_raw, dias_mora_raw, periodicidad_capital, calificacion, gestor, fecha_corte
            )
            VALUES (
              %(agencia)s, %(numero_credito_raw)s, %(linea_credito)s, %(numero_identificacion)s, %(nombre_asociado)s,
              %(saldo_capital_raw)s, %(dias_mora_raw)s, %(periodicidad_capital)s, %(calificacion)s, %(gestor)s, %(fecha_corte)s
            )
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_llamadas_detalle (link)")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    agencia = request.query_params.get('agencia')
    gestor = request.query_params.get('gestor')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM l.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM l.fecha_corte) = %(month)s::int")
        params['month'] = month
    if agencia:
        where.append("l.agencia ILIKE %(agencia)s")
        params['agencia'] = f"%{agencia}%"
    if gestor:
        where.append("l.gestor ILIKE %(gestor)s")
        params['gestor'] = f"%{gestor}%"
    if search:
        where.append("""
            (
              l.nombre_asociado ILIKE %(search)s OR
              l.numero_identificacion ILIKE %(search)s OR
              l.numero_credito_raw ILIKE %(search)s OR
              l.linea_credito ILIKE %(search)s OR
              l.agencia ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            l.id,
            l.fecha_corte,
            l.agencia,
            l.numero_credito_raw AS numero_credito,
            l.linea_credito,
            l.numero_identificacion,
            l.nombre_asociado,
            l.saldo_capital_raw,
            l.dias_mora_raw,
            l.periodicidad_capital,
            l.calificacion,
            l.gestor,
            l.created_at
        FROM cartera.stg_llamadas_detalle l
        {where_sql}
        ORDER BY l.id ASC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_llamadas_detalle',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'agencia': agencia, 'gestor': gestor, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_llamadas_detalle (link)")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cartera_link_visitas(request):
    """
    Lee cartera.stg_visitas_link (link de visitas).
    Filtros opcionales: year/mes (fecha_corte), agencia, asesor, search.
    POST: inserta fila básica.
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['agencia', 'numero_credito_raw', 'linea_credito', 'numero_identificacion', 'nombre_asociado']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO cartera.stg_visitas_link (
              agencia, numero_credito_raw, linea_credito, numero_identificacion, nombre_asociado,
              saldo_capital_raw, dias_mora_raw, periodicidad_capital, dias_actualizados_raw, asesor, fecha_corte
            )
            VALUES (
              %(agencia)s, %(numero_credito_raw)s, %(linea_credito)s, %(numero_identificacion)s, %(nombre_asociado)s,
              %(saldo_capital_raw)s, %(dias_mora_raw)s, %(periodicidad_capital)s, %(dias_actualizados_raw)s, %(asesor)s, %(fecha_corte)s
            )
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_visitas_link")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    agencia = request.query_params.get('agencia')
    asesor = request.query_params.get('asesor')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM l.fecha_corte) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM l.fecha_corte) = %(month)s::int")
        params['month'] = month
    if agencia:
        where.append("l.agencia ILIKE %(agencia)s")
        params['agencia'] = f"%{agencia}%"
    if asesor:
        where.append("l.asesor ILIKE %(asesor)s")
        params['asesor'] = f"%{asesor}%"
    if search:
        where.append("""
            (
              l.nombre_asociado ILIKE %(search)s OR
              l.numero_identificacion ILIKE %(search)s OR
              l.numero_credito_raw ILIKE %(search)s OR
              l.linea_credito ILIKE %(search)s OR
              l.agencia ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            l.id,
            l.fecha_corte,
            l.agencia,
            l.numero_credito_raw AS numero_credito,
            l.linea_credito,
            l.numero_identificacion,
            l.nombre_asociado,
            l.saldo_capital_raw,
            l.dias_mora_raw,
            l.periodicidad_capital,
            COALESCE(l.dias_actualizados_raw, l."DIAS ACTUALIZADOS") AS dias_actualizados,
            l.asesor,
            l.created_at
        FROM cartera.stg_visitas_link l
        {where_sql}
        ORDER BY l.id ASC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_visitas_link',
            'count': len(items),
            'items': items,
            'filters': {
                'year': year,
                'month': month,
                'agencia': agencia,
                'asesor': asesor,
                'search': search,
                'limit': limit
            },
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_visitas_link")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cartera_seguimiento_campanas(request):
    """
    Lee cartera.stg_pagares_paz_y_salvo (seguimiento de campañas).
    Filtros opcionales: year/mes (fecha_carga), gestor, estado_obligacion, search (nombre/cedula/pagares/oficina).
    POST: inserta fila básica.
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['pagare_virtualcop_raw', 'cedula_raw', 'nombre', 'estado_obligacion']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO cartera.stg_pagares_paz_y_salvo (
              oficina, pagare_virtualcop_raw, pagare_opa_raw, cedula_raw, nombre,
              saldo_capital_raw, capital_condonado_raw, estado_obligacion, novedad, fecha_raw,
              gestor, honorarios_raw, abogado, fuente_archivo, fecha_carga
            )
            VALUES (
              %(oficina)s, %(pagare_virtualcop_raw)s, %(pagare_opa_raw)s, %(cedula_raw)s, %(nombre)s,
              %(saldo_capital_raw)s, %(capital_condonado_raw)s, %(estado_obligacion)s, %(novedad)s, %(fecha_raw)s,
              %(gestor)s, %(honorarios_raw)s, %(abogado)s, %(fuente_archivo)s, %(fecha_carga)s
            )
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_pagares_paz_y_salvo")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    gestor = request.query_params.get('gestor')
    estado = request.query_params.get('estado') or request.query_params.get('estado_obligacion')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM p.fecha_carga) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM p.fecha_carga) = %(month)s::int")
        params['month'] = month
    if gestor:
        where.append("p.gestor ILIKE %(gestor)s")
        params['gestor'] = f"%{gestor}%"
    if estado:
        where.append("p.estado_obligacion ILIKE %(estado)s")
        params['estado'] = f"%{estado}%"
    if search:
        where.append("""
            (
              p.nombre ILIKE %(search)s OR
              p.cedula_raw ILIKE %(search)s OR
              p.pagare_virtualcop_raw ILIKE %(search)s OR
              p.pagare_opa_raw ILIKE %(search)s OR
              p.oficina ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            p.id,
            p.oficina,
            p.pagare_virtualcop_raw,
            p.pagare_opa_raw,
            p.cedula_raw,
            p.nombre,
            p.saldo_capital_raw,
            p.capital_condonado_raw,
            p.estado_obligacion,
            p.novedad,
            p.fecha_raw,
            p.gestor,
            p.honorarios_raw,
            p.abogado,
            p.fuente_archivo,
            p.fecha_carga
        FROM cartera.stg_pagares_paz_y_salvo p
        {where_sql}
        ORDER BY p.id ASC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_pagares_paz_y_salvo',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'gestor': gestor, 'estado': estado, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_pagares_paz_y_salvo (seguimiento campañas)")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cartera_gestiones(request):
    """
    Lee cartera.stg_gestiones ajustada al formulario de gestiones.
    Filtros opcionales: year/mes (fecha_gestion o fecha_corte), gestor/usuario_gestion, tipo, search (comentario, cédula, nombre, nro_producto, oficina).
    POST: inserta fila básica.
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['tipo', 'comentario', 'nro_producto', 'cedula', 'nombre', 'usuario_gestion']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO cartera.stg_gestiones (
              fecha_gestion, tipo, comentario, nro_producto, cedula, nombre,
              usuario_gestion, oficina, gestion_validada, gestor, gestiones_efectuadas
            )
            VALUES (
              %(fecha_gestion)s, %(tipo)s, %(comentario)s, %(nro_producto)s, %(cedula)s, %(nombre)s,
              %(usuario_gestion)s, %(oficina)s, %(gestion_validada)s, %(gestor)s, %(gestiones_efectuadas)s
            )
            RETURNING id
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando en cartera.stg_gestiones")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    gestor = request.query_params.get('gestor') or request.query_params.get('usuario_gestion')
    tipo = request.query_params.get('tipo')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '500'))
    except Exception:
        limit = 500
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("""
            (
              (fecha_gestion IS NOT NULL AND EXTRACT(YEAR FROM fecha_gestion) = %(year)s::int)
              OR (fecha_gestion IS NULL AND fecha_corte IS NOT NULL AND EXTRACT(YEAR FROM fecha_corte) = %(year)s::int)
            )
        """)
        params['year'] = year
    if month:
        where.append("""
            (
              (fecha_gestion IS NOT NULL AND EXTRACT(MONTH FROM fecha_gestion) = %(month)s::int)
              OR (fecha_gestion IS NULL AND fecha_corte IS NOT NULL AND EXTRACT(MONTH FROM fecha_corte) = %(month)s::int)
            )
        """)
        params['month'] = month
    if gestor:
        where.append("(usuario_gestion ILIKE %(gestor)s OR gestor ILIKE %(gestor)s)")
        params['gestor'] = f"%{gestor}%"
    if tipo:
        where.append("tipo ILIKE %(tipo)s")
        params['tipo'] = f"%{tipo}%"
    if search:
        where.append("""
            (
              comentario ILIKE %(search)s OR
              cedula ILIKE %(search)s OR
              nombre ILIKE %(search)s OR
              nro_producto ILIKE %(search)s OR
              oficina ILIKE %(search)s OR
              usuario_gestion ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            id,
            COALESCE(fecha_gestion, fecha_corte) AS fecha_gestion,
            tipo,
            comentario,
            nro_producto,
            cedula,
            nombre,
            usuario_gestion,
            oficina,
            gestion_validada,
            gestor,
            gestiones_efectuadas,
            created_at
        FROM cartera.stg_gestiones
        {where_sql}
        ORDER BY id ASC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'cartera.stg_gestiones',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'gestor': gestor, 'tipo': tipo, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo cartera.stg_gestiones")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ing_org_encuesta_satisfaccion(request):
    """
    Lee ingenieria_organizacional.io_encuesta_satisfaccion.
    Filtros opcionales: year/mes (fecha_inicio), oficina_area, search (nombre/correo).
    POST: inserta encuesta (obligatorio: fecha_inicio, correo_electronico, nombre, oficina_area).
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['fecha_inicio', 'correo_electronico', 'nombre', 'oficina_area']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO ingenieria_organizacional.io_encuesta_satisfaccion (
              fecha_inicio, fecha_fin, correo_electronico, nombre, oficina_area,
              calidad_documentos, claridad_comunicacion, rapidez_respuesta, satisfaccion_general,
              tiempo_creacion_texto, apertura_ajustes_texto, comentario_mejora
            )
            VALUES (
              %(fecha_inicio)s, %(fecha_fin)s, %(correo_electronico)s, %(nombre)s, %(oficina_area)s,
              %(calidad_documentos)s, %(claridad_comunicacion)s, %(rapidez_respuesta)s, %(satisfaccion_general)s,
              %(tiempo_creacion_texto)s, %(apertura_ajustes_texto)s, %(comentario_mejora)s
            )
            RETURNING id_encuesta
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando io_encuesta_satisfaccion")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    oficina = request.query_params.get('oficina') or request.query_params.get('oficina_area')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '1000'))
    except Exception:
        limit = 1000
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM e.fecha_inicio) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM e.fecha_inicio) = %(month)s::int")
        params['month'] = month
    if oficina:
        where.append("e.oficina_area ILIKE %(oficina)s")
        params['oficina'] = f"%{oficina}%"
    if search:
        where.append("""
            (
              e.nombre ILIKE %(search)s OR
              e.correo_electronico ILIKE %(search)s OR
              e.oficina_area ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            e.id_encuesta AS id,
            e.fecha_inicio,
            e.fecha_fin,
            e.correo_electronico,
            e.nombre,
            e.oficina_area,
            e.calidad_documentos,
            e.claridad_comunicacion,
            e.rapidez_respuesta,
            e.satisfaccion_general,
            e.tiempo_creacion_texto,
            e.apertura_ajustes_texto,
            e.comentario_mejora
        FROM ingenieria_organizacional.io_encuesta_satisfaccion e
        {where_sql}
        ORDER BY e.fecha_inicio DESC NULLS LAST, e.id_encuesta DESC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'ingenieria_organizacional.io_encuesta_satisfaccion',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'oficina_area': oficina, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo io_encuesta_satisfaccion")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ing_org_documentos(request):
    """
    Lee ingenieria_organizacional.io_documento para listado de maestros.
    Filtros opcionales: estrategia, gestion, tipo_documento, search (nombre/código/proceso).
    POST: inserta documento (obligatorio: estrategia, gestion, tipo_documento, proceso, nombre_documento, codigo, fecha_ultima_actualizacion, version).
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['estrategia', 'gestion', 'tipo_documento', 'proceso', 'nombre_documento', 'codigo', 'fecha_ultima_actualizacion', 'version']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO ingenieria_organizacional.io_documento (
              estrategia, gestion, tipo_documento, proceso, nombre_documento, codigo,
              fecha_ultima_actualizacion, version, porcentaje_actualizado, estado_actualizacion,
              tipo_conservacion, publicado_intranet
            )
            VALUES (
              %(estrategia)s, %(gestion)s, %(tipo_documento)s, %(proceso)s, %(nombre_documento)s, %(codigo)s,
              %(fecha_ultima_actualizacion)s::date, %(version)s, %(porcentaje_actualizado)s, %(estado_actualizacion)s,
              %(tipo_conservacion)s, %(publicado_intranet)s
            )
            RETURNING id_documento
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando io_documento")
            return Response({'error': str(exc)}, status=500)

    estrategia = request.query_params.get('estrategia')
    gestion = request.query_params.get('gestion')
    tipo = request.query_params.get('tipo') or request.query_params.get('tipo_documento')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '1000'))
    except Exception:
        limit = 1000
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if estrategia:
        where.append("d.estrategia ILIKE %(estrategia)s")
        params['estrategia'] = f"%{estrategia}%"
    if gestion:
        where.append("d.gestion ILIKE %(gestion)s")
        params['gestion'] = f"%{gestion}%"
    if tipo:
        where.append("d.tipo_documento ILIKE %(tipo)s")
        params['tipo'] = f"%{tipo}%"
    if search:
        where.append("""
            (
              d.nombre_documento ILIKE %(search)s OR
              d.codigo ILIKE %(search)s OR
              d.proceso ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            d.id_documento AS id,
            d.estrategia,
            d.gestion,
            d.tipo_documento,
            d.proceso,
            d.nombre_documento,
            d.codigo,
            d.fecha_ultima_actualizacion,
            d.version,
            d.porcentaje_actualizado,
            d.estado_actualizacion,
            d.tipo_conservacion,
            d.publicado_intranet
        FROM ingenieria_organizacional.io_documento d
        {where_sql}
        ORDER BY d.fecha_ultima_actualizacion DESC NULLS LAST, d.id_documento DESC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'ingenieria_organizacional.io_documento',
            'count': len(items),
            'items': items,
            'filters': {'estrategia': estrategia, 'gestion': gestion, 'tipo': tipo, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo io_documento")
        return Response({'error': str(exc)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ing_org_solicitudes(request):
    """
    Lee ingenieria_organizacional.io_solicitud.
    Filtros opcionales: year/mes (fecha_solicitud), gestion, estado, tipo_solicitud, search (descripcion, creado_por, asignado_a).
    POST: inserta solicitud (obligatorio: radicado, gestion, estado, creado_por, tipo_solicitud, asignado_a, fecha_solicitud).
    """
    if request.method == 'POST':
        p = request.data or {}
        required = ['radicado', 'gestion', 'estado', 'creado_por', 'tipo_solicitud', 'asignado_a', 'fecha_solicitud']
        missing = [k for k in required if not p.get(k)]
        if missing:
            return Response({'error': f"Faltan campos obligatorios: {', '.join(missing)}"}, status=400)
        insert_sql = """
            INSERT INTO ingenieria_organizacional.io_solicitud (
              radicado, mes, gestion, descripcion, avance, estado, creado_por,
              tipo_solicitud, asignado_a, fecha_solicitud, fecha_en_curso, fecha_revision,
              fecha_en_ajustes, fecha_en_aprobacion, fecha_completado, tiene_doc_adjunto
            )
            VALUES (
              %(radicado)s, %(mes)s, %(gestion)s, %(descripcion)s, %(avance)s, %(estado)s, %(creado_por)s,
              %(tipo_solicitud)s, %(asignado_a)s, %(fecha_solicitud)s::date, %(fecha_en_curso)s, %(fecha_revision)s,
              %(fecha_en_ajustes)s, %(fecha_en_aprobacion)s, %(fecha_completado)s, %(tiene_doc_adjunto)s
            )
            RETURNING id_solicitud
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, insert_sql, p)
                new_id = c.fetchone()[0]
            return Response({'id': new_id}, status=201)
        except Exception as exc:
            logger.exception("Error insertando io_solicitud")
            return Response({'error': str(exc)}, status=500)

    year = request.query_params.get('year') or request.query_params.get('anio')
    month = request.query_params.get('month') or request.query_params.get('mes')
    gestion = request.query_params.get('gestion')
    estado = request.query_params.get('estado')
    tipo = request.query_params.get('tipo') or request.query_params.get('tipo_solicitud')
    search = request.query_params.get('search') or request.query_params.get('q')
    try:
        limit = int(request.query_params.get('limit', '1000'))
    except Exception:
        limit = 1000
    limit = max(1, min(limit, 5000))

    where = []
    params = {}
    if year:
        where.append("EXTRACT(YEAR FROM s.fecha_solicitud) = %(year)s::int")
        params['year'] = year
    if month:
        where.append("EXTRACT(MONTH FROM s.fecha_solicitud) = %(month)s::int")
        params['month'] = month
    if gestion:
        where.append("s.gestion ILIKE %(gestion)s")
        params['gestion'] = f"%{gestion}%"
    if estado:
        where.append("s.estado ILIKE %(estado)s")
        params['estado'] = f"%{estado}%"
    if tipo:
        where.append("s.tipo_solicitud ILIKE %(tipo)s")
        params['tipo'] = f"%{tipo}%"
    if search:
        where.append("""
            (
              s.descripcion ILIKE %(search)s OR
              s.creado_por ILIKE %(search)s OR
              s.asignado_a ILIKE %(search)s
            )
        """)
        params['search'] = f"%{search}%"
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT
            s.id_solicitud AS id,
            s.radicado,
            s.mes,
            s.gestion,
            s.descripcion,
            s.avance,
            s.estado,
            s.creado_por,
            s.tipo_solicitud,
            s.asignado_a,
            s.fecha_solicitud,
            s.fecha_en_curso,
            s.fecha_revision,
            s.fecha_en_ajustes,
            s.fecha_en_aprobacion,
            s.fecha_completado,
            s.tiene_doc_adjunto
        FROM ingenieria_organizacional.io_solicitud s
        {where_sql}
        ORDER BY s.fecha_solicitud DESC NULLS LAST, s.id_solicitud DESC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({
            'source': 'ingenieria_organizacional.io_solicitud',
            'count': len(items),
            'items': items,
            'filters': {'year': year, 'month': month, 'gestion': gestion, 'estado': estado, 'tipo': tipo, 'search': search, 'limit': limit},
        })
    except Exception as exc:
        logger.exception("Error leyendo io_solicitud")
        return Response({'error': str(exc)}, status=500)


# ====== Presupuesto ======

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_presupuesto_spec(request):
    """Esquema de la Tabla 3: Presupuesto."""
    spec = {
        'columns': [
            {'key': 'cuenta', 'label': 'Cuenta (Id_cuenta)', 'type': 'string'},
            {'key': 'nombre_cuenta', 'label': 'Nombre de la Cuenta', 'type': 'string'},
            {'key': 'mes', 'label': 'Mes (1-12)', 'type': 'string'},
            {'key': 'anio', 'label': 'Año (YYYY)', 'type': 'string'},
        ]
    }
    return Response(spec)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def finanzas_presupuesto_list(request):
    """Presupuesto en esquema finanzas (tabla: finanzas.presupuesto).

    GET: lista con join a dim_cuenta para nombre_cuenta. Filtros ?year&month.
    POST: upsert por (cuenta, anio, mes) en finanzas.presupuesto.
    """
    if request.method == 'POST':
        from datetime import datetime as pydt
        payload = request.data
        cuenta = (payload.get('cuenta') or '').strip()
        try:
            anio = int(payload.get('anio'))
            mes = int(payload.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes deben ser enteros'}, status=400)
        try:
            presupuesto = float(payload.get('presupuesto'))
        except Exception:
            return Response({'error': 'presupuesto debe ser numérico'}, status=400)
        if not cuenta:
            return Response({'error': 'cuenta es requerida'}, status=400)

        from django.db import connections
        with connections['default'].cursor() as c:
            # Intentar update primero
            c.execute(
                """
                UPDATE finanzas.presupuesto
                SET presupuesto=%s
                WHERE cuenta=%s AND anio=%s AND mes=%s
                """,
                [presupuesto, cuenta, anio, mes],
            )
            if c.rowcount == 0:
                c.execute(
                    """
                    INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [cuenta, anio, mes, presupuesto, pydt.now()],
                )
        return Response({
            'success': True,
            'saved': {
                'cuenta': cuenta,
                'anio': anio,
                'mes': mes,
                'presupuesto': presupuesto,
            }
        }, status=201)

    # GET
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    params = {'year': year, 'month': month}
    where = []
    if year:
        where.append('p.anio = %(year)s::int')
    if month:
        where.append('p.mes = %(month)s::int')
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    sql = f"""
        SELECT p.cuenta::text AS cuenta,
               COALESCE(d.nombre_cuenta, '')::text AS nombre_cuenta,
               p.mes::text AS mes,
               p.anio::text AS anio,
               p.presupuesto::numeric AS presupuesto
        FROM finanzas.presupuesto p
        LEFT JOIN dim_cuenta d ON d.cuenta = p.cuenta
        {where_sql}
        ORDER BY p.anio DESC, p.mes DESC, p.cuenta
    """
    from django.db import connections
    try:
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            items = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({'source': 'finanzas.presupuesto', 'count': len(items), 'items': items, 'filters': {'year': year, 'month': month}})
    except Exception as e:
        return Response({'error': str(e), 'source': 'finanzas.presupuesto'}, status=400)


class PresupuestoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        params = {'year': year, 'month': month}
        where = []
        if year:
            where.append('p.anio = %(year)s::int')
        if month:
            where.append('p.mes = %(month)s::int')
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

        sql = f"""
            SELECT p.id::text AS id,
                   p.cuenta::text AS cuenta,
                   COALESCE(p.denominacion, d.nombre_cuenta, pc.nombre, '')::text AS nombre_cuenta,
                   p.mes::int AS mes,
                   p.anio::int AS anio,
                   p.presupuesto::numeric AS presupuesto,
                   COALESCE(p.monto_historico, p.presupuesto)::numeric AS monto_historico,
                   COALESCE(p.monto_proyectado, p.presupuesto)::numeric AS monto_proyectado,
                   p.created_at::text AS created_at
            FROM finanzas.presupuesto p
            LEFT JOIN dim_cuenta d ON d.cuenta = p.cuenta
            LEFT JOIN plan_cuentas pc ON pc.cuenta = p.cuenta
            {where_sql}
            ORDER BY p.anio DESC, p.mes DESC, p.cuenta
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, sql, params)
                cols = [col[0] for col in c.description]
                items = [dict(zip(cols, row)) for row in c.fetchall()]
            return Response({'source': 'finanzas.presupuesto', 'count': len(items), 'items': items, 'filters': {'year': year, 'month': month}})
        except Exception as e:
            return Response({'error': str(e), 'source': 'finanzas.presupuesto'}, status=400)

    def post(self, request):
        """Crear o actualizar un registro de presupuesto"""
        try:
            data = request.data
            cuenta = data.get('cuenta')
            denominacion = data.get('denominacion', data.get('nombre_cuenta', ''))
            anio = data.get('anio')
            mes = data.get('mes')
            presupuesto = data.get('presupuesto', 0)
            monto_historico = data.get('monto_historico', 0)
            monto_proyectado = data.get('monto_proyectado', 0)

            # Validar campos requeridos
            if not cuenta or not anio or not mes:
                return Response({'error': 'Cuenta, año y mes son campos requeridos'}, status=400)

            # Convertir a tipos correctos
            try:
                anio = int(anio)
                mes = int(mes)
                presupuesto = float(presupuesto) if presupuesto else 0.0
                monto_historico = float(monto_historico) if monto_historico else 0.0
                monto_proyectado = float(monto_proyectado) if monto_proyectado else 0.0
            except (ValueError, TypeError):
                return Response({'error': 'Año, mes y montos deben ser números válidos'}, status=400)

            with connections['default'].cursor() as c:
                # Intentar actualizar primero
                c.execute("""
                    UPDATE finanzas.presupuesto 
                    SET presupuesto = %s, monto_historico = %s, monto_proyectado = %s, denominacion = %s
                    WHERE cuenta = %s AND anio = %s AND mes = %s
                """, [presupuesto, monto_historico, monto_proyectado, denominacion, cuenta, anio, mes])
                
                # Si no se actualizó ninguna fila, insertar nueva
                if c.rowcount == 0:
                    c.execute("""
                        INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, denominacion, monto_historico, monto_proyectado, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, [cuenta, anio, mes, presupuesto, denominacion, monto_historico, monto_proyectado])

            return Response({'message': 'Registro guardado correctamente'}, status=200)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"[PresupuestoView POST] Error: {str(e)}")
            return Response({'error': str(e)}, status=500)

    def delete(self, request, id=None):
        """Eliminar un registro de presupuesto"""
        try:
            # El ID viene en formato "cuenta_anio_mes"
            if not id:
                return Response({'error': 'ID requerido'}, status=400)
            
            try:
                cuenta, anio, mes = id.split('_')
                anio = int(anio)
                mes = int(mes)
            except (ValueError, IndexError):
                return Response({'error': 'ID inválido. Formato esperado: cuenta_anio_mes'}, status=400)

            with connections['default'].cursor() as c:
                # Verificar si el registro existe
                c.execute("""
                    SELECT COUNT(*) FROM finanzas.presupuesto 
                    WHERE cuenta = %s AND anio = %s AND mes = %s
                """, [cuenta, anio, mes])
                
                if c.fetchone()[0] == 0:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                
                # Eliminar el registro
                c.execute("""
                    DELETE FROM finanzas.presupuesto 
                    WHERE cuenta = %s AND anio = %s AND mes = %s
                """, [cuenta, anio, mes])

            return Response({'message': 'Registro eliminado correctamente'}, status=200)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"[PresupuestoView DELETE] Error: {str(e)}")
            return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cuentas_disponibles(request):
    """GET: Lista todas las cuentas disponibles del plan de cuentas"""
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT cuenta, nombre 
                FROM plan_cuentas 
                ORDER BY cuenta
            """)
            
            cuentas = []
            for row in cursor.fetchall():
                cuentas.append({
                    'cuenta': row[0],
                    'nombre': row[1] or ''
                })
            
            return Response({'cuentas': cuentas}, status=200)
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"[cuentas_disponibles] ERROR: {str(e)}")
        return Response({'error': str(e)}, status=500)


class PresupuestoUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Sube un archivo Excel/CSV con columnas: cuenta, anio, mes, presupuesto [, nombre_cuenta]
        y upserta en finanzas.presupuesto.
        """
        f = request.FILES.get('file')
        if not f:
            return Response({'error': "Archivo 'file' requerido"}, status=400)

        filename = getattr(f, 'name', 'upload')
        imported = 0
        errors = []

        import io, csv
        content = f.read()

        def upsert_row(cuenta, anio, mes, presupuesto):
            from datetime import datetime as pydt
            try:
                anio = int(anio)
                mes = int(mes)
                presupuesto = float(str(presupuesto).replace(',', '.'))
            except Exception:
                return False
            with connections['default'].cursor() as c:
                c.execute(
                    """
                    UPDATE finanzas.presupuesto
                    SET presupuesto=%s
                    WHERE cuenta=%s AND anio=%s AND mes=%s
                    """,
                    [presupuesto, str(cuenta), anio, mes],
                )
                if c.rowcount == 0:
                    c.execute(
                        """
                        INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, created_at)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        [str(cuenta), anio, mes, presupuesto, pydt.now()],
                    )
            return True

        try:
            if filename.lower().endswith('.csv'):
                text = content.decode('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(text))
                for i, row in enumerate(reader, 1):
                    ok = upsert_row(row.get('cuenta'), row.get('anio'), row.get('mes'), row.get('presupuesto'))
                    if ok:
                        imported += 1
                    else:
                        errors.append(f'Fila {i}: datos inválidos')
            else:
                # Intentar XLSX con openpyxl
                try:
                    import openpyxl
                except Exception:
                    return Response({'error': 'Para archivos .xlsx se requiere openpyxl. Sube CSV o instala openpyxl.'}, status=400)
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                # Buscar encabezados
                headers = {}
                for j, cell in enumerate(next(ws.iter_rows(min_row=1, max_row=1, values_only=True))):
                    if not cell:
                        continue
                    headers[str(cell).strip().lower()] = j
                required = ['cuenta', 'anio', 'mes', 'presupuesto']
                if not all(k in headers for k in required):
                    return Response({'error': 'Encabezados requeridos: cuenta, anio, mes, presupuesto'}, status=400)
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    values = {k: row[headers[k]] if headers.get(k) is not None else None for k in required}
                    ok = upsert_row(values['cuenta'], values['anio'], values['mes'], values['presupuesto'])
                    if ok: imported += 1
                    else: errors.append(f'Fila {i}: datos inválidos')
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({'success': True, 'imported': imported, 'errors': errors})

    def post(self, request):
        from datetime import datetime as pydt
        payload = request.data
        cuenta = (payload.get('cuenta') or '').strip()
        try:
            anio = int(payload.get('anio'))
            mes = int(payload.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes deben ser enteros'}, status=400)
        try:
            presupuesto = float(payload.get('presupuesto'))
        except Exception:
            return Response({'error': 'presupuesto debe ser numérico'}, status=400)
        if not cuenta:
            return Response({'error': 'cuenta es requerida'}, status=400)

        with connections['default'].cursor() as c:
            c.execute(
                """
                UPDATE finanzas.presupuesto
                SET presupuesto=%s
                WHERE cuenta=%s AND anio=%s AND mes=%s
                """,
                [presupuesto, cuenta, anio, mes],
            )
            if c.rowcount == 0:
                c.execute(
                    """
                    INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [cuenta, anio, mes, presupuesto, pydt.now()],
                )
        return Response({'success': True, 'saved': {'cuenta': cuenta, 'anio': anio, 'mes': mes, 'presupuesto': presupuesto}}, status=201)


class PresupuestoUploadSimpleView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Sube un Excel/CSV con columnas: Código, Denominación, Proyectado.
        Año y Mes vienen en el form. Upsert a finanzas.presupuesto (presupuesto=Proyectado, denominacion).
        """
        f = request.FILES.get('file')
        if not f:
            return Response({'error': "Archivo 'file' requerido"}, status=400)
        try:
            anio = int(request.POST.get('anio'))
            mes = int(request.POST.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes requeridos y numéricos'}, status=400)
        if not (1 <= mes <= 12):
            return Response({'error': 'mes inválido (1-12)'}, status=400)

        import io, csv, re
        content = f.read()

        uploaded_meta = {
            'original_name': getattr(f, 'name', ''),
            'saved_name': None,
            'uploaded_at': None,
        }

        # Guardar el archivo subido bajo LIBRO_BALANCE_ROOT/Presupuesto/Aanoo_<anio>/
        try:
            root = _get_balance_root()
            target_dir = root / 'Presupuesto' / f'Aanoo_{anio}'
            target_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime as pydt
            timestamp = pydt.now()
            original_name = Path(f.name or '').name or 'presupuesto.xlsx'
            base_name = Path(original_name).stem or 'presupuesto'
            ext = Path(original_name).suffix or '.xlsx'
            clean_base = re.sub(r'[^A-Za-z0-9._-]+', '_', base_name).strip('_') or 'presupuesto'
            candidate = f"{clean_base}{ext}"
            dest_path = target_dir / candidate
            counter = 1
            while dest_path.exists():
                candidate = f"{clean_base}_{counter}{ext}"
                dest_path = target_dir / candidate
                counter += 1
            with open(dest_path, 'wb+') as dst:
                dst.write(content)
            try:
                saved_rel = dest_path.relative_to(root).as_posix()
            except Exception:
                saved_rel = dest_path.name
            uploaded_meta['saved_name'] = dest_path.name
            uploaded_meta['uploaded_at'] = timestamp.isoformat()
        except Exception:
            # No es bloqueante: si falla el guardado del archivo, continuar con la carga lógica
            saved_rel = None

        def norm_code(x):
            if x is None:
                return None
            s = re.sub(r'\D', '', str(x))
            return s or None

        def norm_num(x):
            if x in (None, ''):
                return None
            s = str(x).replace('\u00a0',' ').replace(' ','').replace('.','')
            s = s.replace(',', '.')
            try:
                return float(s)
            except Exception:
                return None

        def upsert_row(cuenta, denom, proyectado):
            if not cuenta:
                return False
            try:
                with connections['default'].cursor() as c:
                    c.execute(
                        """
                        UPDATE finanzas.presupuesto
                        SET presupuesto = %s, denominacion = COALESCE(%s, denominacion)
                        WHERE cuenta = %s AND anio = %s AND mes = %s
                        """,
                        [proyectado, denom or None, cuenta, anio, mes]
                    )
                    if c.rowcount == 0:
                        from datetime import datetime as pydt
                        c.execute(
                            """
                            INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, denominacion, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            [cuenta, anio, mes, proyectado or 0, denom or None, pydt.now()]
                        )
                return True
            except Exception:
                return False

        imported = 0
        errors = []

        try:
            filename = getattr(f, 'name', 'upload')
            if filename.lower().endswith('.csv'):
                text = content.decode('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(text))
                for i, row in enumerate(reader, 2):
                    lower = { (k or '').strip().lower(): v for k, v in row.items() }
                    def find_by_tokens(d, tokens):
                        for key in d.keys():
                            if all(tok in key for tok in tokens):
                                return d.get(key)
                        return None
                    codigo = norm_code(find_by_tokens(lower, ['codigo']) or lower.get('cuenta'))
                    denom = (find_by_tokens(lower, ['denomin']) or find_by_tokens(lower, ['nombre'])) or ''
                    proj = norm_num(find_by_tokens(lower, ['proyect']) or lower.get('monto'))
                    if not codigo:
                        continue
                    ok = upsert_row(codigo, denom, proj)
                    imported += 1 if ok else 0
            else:
                try:
                    import openpyxl
                except Exception:
                    return Response({'error': 'Para .xlsx se requiere openpyxl. Sube CSV o instala openpyxl.'}, status=400)
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                max_scan_rows = min(6, ws.max_row)
                max_cols = ws.max_column
                col_texts = []
                for cidx in range(1, max_cols + 1):
                    parts = []
                    for ridx in range(1, max_scan_rows + 1):
                        v = ws.cell(ridx, cidx).value
                        if v is None:
                            continue
                        s = str(v).strip()
                        if s:
                            parts.append(s)
                    col_texts.append(' '.join(parts).lower())
                def find_idx(pred):
                    for idx, t in enumerate(col_texts):
                        try:
                            if pred(t):
                                return idx
                        except Exception:
                            pass
                    return None
                i_cod = find_idx(lambda t: 'codigo' in t or 'código' in t or 'cuenta' in t)
                i_den = find_idx(lambda t: 'denomin' in t or 'nombre' in t)
                i_pro = find_idx(lambda t: ('proyect' in t) and ('hist' not in t))
                if i_cod is None or i_den is None or i_pro is None:
                    return Response({'error': 'Encabezados requeridos: código, denominación y proyectado'}, status=400)
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    codigo = norm_code(row[i_cod] if i_cod is not None else None)
                    denom = (row[i_den] if i_den is not None else '') or ''
                    proj = norm_num(row[i_pro] if i_pro is not None else None)
                    if not codigo:
                        continue
                    ok = upsert_row(codigo, denom, proj)
                    imported += 1 if ok else 0
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({
            'success': True,
            'imported': imported,
            'errors': errors,
            'saved_rel': saved_rel,
            'uploaded_meta': uploaded_meta,
        })


class PresupuestoExecuteFileView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Ejecuta el ETL de presupuesto leyendo un archivo ya guardado en disco.
        Body JSON: { rel: 'Presupuesto/Aanoo_2025/archivo.xlsx', anio: 2025, mes: 10 }
        """
        rel = (request.data.get('rel') or '').strip()
        try:
            anio = int(request.data.get('anio'))
            mes = int(request.data.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes requeridos y numéricos'}, status=400)
        if not rel:
            return Response({'error': 'rel es requerido'}, status=400)
        if not (1 <= mes <= 12):
            return Response({'error': 'mes inválido (1-12)'}, status=400)

        root = _get_balance_root()
        fpath = (root / rel).resolve(strict=False)
        try:
            # Validar que fpath esté bajo root
            _ = fpath.relative_to(root)
        except Exception:
            return Response({'error': 'Ruta fuera de la raíz permitida'}, status=400)
        if not fpath.exists():
            return Response({'error': 'Archivo no encontrado'}, status=404)

        import io, csv, re

        def norm_code(x):
            if x is None:
                return None
            s = re.sub(r'\D', '', str(x))
            return s or None

        def norm_num(x):
            if x in (None, ''):
                return None
            s = str(x).replace('\u00a0',' ').replace(' ','').replace('.','')
            s = s.replace(',', '.')
            try:
                return float(s)
            except Exception:
                return None

        # Asegurar tabla auxiliar presupuesto_app disponible
        _ensure_presupuesto_app_table()

        def upsert_row(cuenta, denom, proyectado):
            if not cuenta:
                return False
            try:
                with connections['default'].cursor() as c:
                    c.execute(
                        """
                        UPDATE finanzas.presupuesto
                        SET presupuesto = %s, denominacion = COALESCE(%s, denominacion)
                        WHERE cuenta = %s AND anio = %s AND mes = %s
                        """,
                        [proyectado, denom or None, cuenta, anio, mes]
                    )
                    if c.rowcount == 0:
                        from datetime import datetime as pydt
                        c.execute(
                            """
                            INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, denominacion, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            [cuenta, anio, mes, proyectado or 0, denom or None, pydt.now()]
                        )
                    # También reflejar en finanzas.presupuesto_app que es lo que lista el front
                    c.execute(
                        """
                        UPDATE finanzas.presupuesto_app
                           SET denominacion = COALESCE(%s, denominacion),
                               proyectado = COALESCE(%s, proyectado)
                         WHERE cuenta = %s AND anio = %s AND mes = %s
                        """,
                        [denom or None, proyectado, cuenta, anio, mes]
                    )
                    if c.rowcount == 0:
                        c.execute(
                            """
                            INSERT INTO finanzas.presupuesto_app (cuenta, denominacion, anio, mes, proyectado, historico)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            [cuenta, denom or '', anio, mes, proyectado or 0, 0]
                        )
                return True
            except Exception:
                return False

        imported = 0
        try:
            if fpath.suffix.lower() == '.csv':
                text = fpath.read_text('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    lower = { (k or '').strip().lower(): v for k, v in row.items() }
                    def find_by_tokens(d, tokens):
                        for key in d.keys():
                            if all(tok in key for tok in tokens):
                                return d.get(key)
                        return None
                    codigo = norm_code(find_by_tokens(lower, ['codigo']) or lower.get('cuenta'))
                    denom = (find_by_tokens(lower, ['denomin']) or find_by_tokens(lower, ['nombre'])) or ''
                    proj = norm_num(find_by_tokens(lower, ['proyect']) or lower.get('monto'))
                    if not codigo:
                        continue
                    if upsert_row(codigo, denom, proj):
                        imported += 1
            else:
                try:
                    import openpyxl
                except Exception:
                    return Response({'error': 'Para .xlsx se requiere openpyxl'}, status=400)
                wb = openpyxl.load_workbook(str(fpath), data_only=True)
                ws = wb.active
                max_scan_rows = min(6, ws.max_row)
                max_cols = ws.max_column
                col_texts = []
                for cidx in range(1, max_cols + 1):
                    parts = []
                    for ridx in range(1, max_scan_rows + 1):
                        v = ws.cell(ridx, cidx).value
                        if v is None:
                            continue
                        s = str(v).strip()
                        if s:
                            parts.append(s)
                    col_texts.append(' '.join(parts).lower())
                def find_idx(pred):
                    for idx, t in enumerate(col_texts):
                        try:
                            if pred(t):
                                return idx
                        except Exception:
                            pass
                    return None
                i_cod = find_idx(lambda t: 'codigo' in t or 'código' in t or 'cuenta' in t)
                i_den = find_idx(lambda t: 'denomin' in t or 'nombre' in t)
                i_pro = find_idx(lambda t: ('proyect' in t) and ('hist' not in t))
                if i_cod is None or i_den is None or i_pro is None:
                    return Response({'error': 'Encabezados requeridos: código, denominación y proyectado'}, status=400)
                for row in ws.iter_rows(min_row=2, values_only=True):
                    codigo = norm_code(row[i_cod] if i_cod is not None else None)
                    denom = (row[i_den] if i_den is not None else '') or ''
                    proj = norm_num(row[i_pro] if i_pro is not None else None)
                    if not codigo:
                        continue
                    if upsert_row(codigo, denom, proj):
                        imported += 1
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({'success': True, 'imported': imported})
@api_view(['GET'])
@permission_classes([AllowAny])
def presupuesto_files(request):
    """Lista archivos subidos para presupuesto simple, agrupados por año.
    Ubicación: LIBRO_BALANCE_ROOT/Presupuesto/Aanoo_<anio>
    """
    year = request.query_params.get('year')
    root = _get_balance_root()
    base = root / 'Presupuesto'
    out = []
    try:
        if not base.exists():
            return Response({'files': out})
        dirs = sorted([p for p in base.glob('Aanoo_*') if p.is_dir()])
        for d in dirs:
            y = d.name.replace('Aanoo_', '')
            if year and str(year) != y:
                continue
            items = []
            files = []
            for pat in ('*.xls', '*.xlsx', '*.csv'):
                files.extend(sorted(d.glob(pat)))
            for f in files:
                try:
                    rel = f.relative_to(root).as_posix()
                except Exception:
                    try:
                        rel = f.relative_to(base.parent).as_posix()
                    except Exception:
                        rel = f.name
                items.append({'name': f.name, 'rel': rel})
            out.append({'year': y, 'path': d.relative_to(root).as_posix(), 'files': items})
        return Response({'files': out})
    except Exception as e:
        # No romper el flujo del front; retornar lista vacía con el error para diagnóstico
        return Response({'error': str(e), 'files': []})


# ====== Indicadores Consolidados ======

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finanzas_indicadores_consolidados(request):
    """Indicadores Consolidados desde vistas de BI (prioridad finanzas.vw_indicadores_completos → datamart.vw_indicadores_financieros → finan.vw_oficina_indicadores_mes agregada)."""
    year = int(request.query_params.get('year', datetime.now().year))
    month = int(request.query_params.get('month', datetime.now().month))
    chosen = _choose_view([
        ('finanzas', 'vw_indicadores_completos'),
        ('datamart', 'vw_indicadores_financieros'),
        ('finan', 'vw_oficina_indicadores_mes'),
    ])
    if not chosen:
        return Response({'source': 'none', 'items': []})

    if chosen.endswith('finanzas.vw_indicadores_completos'):
        # Agregamos por nombre_indicador y periodo desde la vista de finanzas
        sql = """
            WITH base AS (
                SELECT nombre_indicador::text,
                       formula::text AS formula_indicador,
                       anio::int, mes::int,
                       AVG(valor_calculado) AS valor
                FROM finanzas.vw_indicadores_completos
                WHERE (anio=%(year)s AND mes=%(month)s)
                   OR (anio=%(year)s-1 AND mes IN (12, %(month)s))
                   OR (anio=%(year)s-2 AND mes=%(month)s)
                   OR (anio=%(year)s-3 AND mes=%(month)s)
                GROUP BY nombre_indicador, formula, anio, mes
            )
            SELECT b0.nombre_indicador,
                   COALESCE(b0.formula_indicador, b1.formula_indicador, b2.formula_indicador, b3.formula_indicador, b4.formula_indicador) AS formula_indicador,
                   b0.valor AS valor_mes_actual,
                   b1.valor AS valor_dic_anterior,
                   b2.valor AS valor_mes_aa,
                   b3.valor AS valor_mes_aa2,
                   b4.valor AS valor_mes_aa3,
                   COALESCE(ii.interpretacion, '')::text AS analisis
            FROM base b0
            LEFT JOIN base b1 ON b1.nombre_indicador=b0.nombre_indicador AND b1.anio=%(year)s-1 AND b1.mes=12
            LEFT JOIN base b2 ON b2.nombre_indicador=b0.nombre_indicador AND b2.anio=%(year)s-1 AND b2.mes=%(month)s
            LEFT JOIN base b3 ON b3.nombre_indicador=b0.nombre_indicador AND b3.anio=%(year)s-2 AND b3.mes=%(month)s
            LEFT JOIN base b4 ON b4.nombre_indicador=b0.nombre_indicador AND b4.anio=%(year)s-3 AND b4.mes=%(month)s
            LEFT JOIN indicadores_interpretacion ii ON ii.indicador=b0.nombre_indicador AND ii.anio=%(year)s AND ii.mes=%(month)s
            WHERE b0.anio=%(year)s AND b0.mes=%(month)s
            ORDER BY b0.nombre_indicador
        """
        params = {'year': year, 'month': month}
    elif chosen.endswith('datamart.vw_indicadores_financieros'):
        sql = """
            SELECT 
                v.nombre_indicador::text,
                v.formula_indicador::text,
                v.valor_indicador_actual::numeric AS valor_mes_actual,
                v.valor_dic_anio_anterior::numeric AS valor_dic_anterior,
                v.valor_mismo_mes_1a::numeric AS valor_mes_aa,
                v.valor_mismo_mes_2a::numeric AS valor_mes_aa2,
                v.valor_mismo_mes_3a::numeric AS valor_mes_aa3,
                COALESCE(ii.interpretacion, '')::text AS analisis
            FROM datamart.vw_indicadores_financieros v
            LEFT JOIN indicadores_interpretacion ii
              ON ii.indicador = v.nombre_indicador AND ii.anio = v.anio AND ii.mes = v.mes
            WHERE v.anio = %(year)s::int AND v.mes = %(month)s::int
            ORDER BY v.nombre_indicador
        """
        params = {'year': year, 'month': month}
    elif chosen.endswith('finan.vw_oficina_indicadores_mes'):
        # Agregar por indicador promedio de valor para el mes, y construir históricos relativos
        sql = """
            WITH base AS (
                SELECT indicador::text AS nombre_indicador,
                       %(year)s::int AS anio, %(month)s::int AS mes,
                       AVG(CASE WHEN anio=%(year)s AND mes=%(month)s THEN valor END) AS valor_mes_actual,
                       AVG(CASE WHEN anio=%(year)s-1 AND mes=12 THEN valor END) AS valor_dic_anterior,
                       AVG(CASE WHEN anio=%(year)s-1 AND mes=%(month)s THEN valor END) AS valor_mes_aa,
                       AVG(CASE WHEN anio=%(year)s-2 AND mes=%(month)s THEN valor END) AS valor_mes_aa2,
                       AVG(CASE WHEN anio=%(year)s-3 AND mes=%(month)s THEN valor END) AS valor_mes_aa3
                FROM finan.vw_oficina_indicadores_mes
                WHERE (anio=%(year)s AND mes=%(month)s)
                   OR (anio=%(year)s-1 AND mes IN (12, %(month)s))
                   OR (anio=%(year)s-2 AND mes=%(month)s)
                   OR (anio=%(year)s-3 AND mes=%(month)s)
                GROUP BY indicador
            )
            SELECT b.nombre_indicador,
                   f.formula_indicador::text,
                   b.valor_mes_actual::numeric,
                   b.valor_dic_anterior::numeric,
                   b.valor_mes_aa::numeric,
                   b.valor_mes_aa2::numeric,
                   b.valor_mes_aa3::numeric,
                   COALESCE(ii.interpretacion, '')::text AS analisis
            FROM base b
            LEFT JOIN indicadores_financieros f ON f.nombre_indicador = b.nombre_indicador
            LEFT JOIN indicadores_interpretacion ii ON ii.indicador = b.nombre_indicador AND ii.anio=%(year)s AND ii.mes=%(month)s
            ORDER BY b.nombre_indicador
        """
        params = {'year': year, 'month': month}
    else:
        # Caso genérico para finanzas.vw_indicadores_completos con nombres esperados
        sql = """
            SELECT nombre_indicador::text,
                   formula_indicador::text,
                   valor_mes_actual::numeric,
                   valor_dic_anterior::numeric,
                   valor_mes_aa::numeric,
                   valor_mes_aa2::numeric,
                   valor_mes_aa3::numeric,
                   COALESCE(analisis, '')::text AS analisis
            FROM finanzas.vw_indicadores_completos
            WHERE anio=%(year)s::int AND mes=%(month)s::int
            ORDER BY nombre_indicador
        """
        params = {'year': year, 'month': month}

    with connections['default'].cursor() as c:
        _exec(c, sql, params)
        cols = [col[0] for col in c.description]
        items = [dict(zip(cols, row)) for row in c.fetchall()]
    return Response({'year': year, 'month': month, 'items': items, 'source': chosen})


class IndicadoresAnalisisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Guarda/actualiza el análisis para un indicador en (anio, mes)."""
        data = request.data
        indicador = data.get('indicador') or data.get('nombre_indicador')
        try:
            anio = int(data.get('anio'))
            mes = int(data.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes deben ser enteros'}, status=400)
        analisis = (data.get('analisis') or '').strip()
        if not indicador:
            return Response({'error': 'indicador es requerido'}, status=400)
        with connections['default'].cursor() as c:
            c.execute(
                """
                UPDATE indicadores_interpretacion
                SET interpretacion=%s, updated_at=NOW()
                WHERE indicador=%s AND anio=%s AND mes=%s
                """,
                [analisis, indicador, anio, mes],
            )
            if c.rowcount == 0:
                c.execute(
                    """
                    INSERT INTO indicadores_interpretacion (indicador, anio, mes, interpretacion, updated_at)
                    VALUES (%s,%s,%s,%s,NOW())
                    """,
                    [indicador, anio, mes, analisis],
                )
        return Response({'success': True})


# ====== Indicadores Comparativa (tabla dedicada en finanzas) ======

"""
-------------------------------------
 Bloque de lógica principal
 Indicadores: tabla comparativa
-------------------------------------
"""
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def indicadores_comparativa(request):
    """CRUD sobre finanzas.indicadores_comparativa
       - GET: lista con filtros ?year=&month=&indicador=&limit=
       - POST: upsert por (indicador, anio, mes)
       - PUT: update por id, o por (indicador, anio, mes)
       - DELETE: elimina por (indicador, anio, mes)

       Campos soportados en body:
         indicador|nombre_indicador, anio, mes, periodo?, alcance?,
         mesActual?, diciembre1a?, mes1a?, mes2a?, analisis?
    """
    from hashlib import md5

    _ensure_indicadores_comparativa_table()

    # Utilidades de mes
    MONTHS_MAP = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    }
    MONTHS_INV = {v: k.capitalize() for k, v in MONTHS_MAP.items()}

    # Expresiones SQL reutilizables: mes/anio → int
    CASE_MONTH_TO_INT = (
        "CASE\n"
        "  WHEN NULLIF(TRIM((mes)::text),'') ~ '^[0-9]+' THEN (NULLIF(TRIM((mes)::text),'')::int)\n"
        "  WHEN LOWER(NULLIF(TRIM((mes)::text),'')) IN ('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','setiembre','octubre','noviembre','diciembre') THEN\n"
        "    CASE LOWER(NULLIF(TRIM((mes)::text),''))\n"
        "      WHEN 'enero' THEN 1 WHEN 'febrero' THEN 2 WHEN 'marzo' THEN 3 WHEN 'abril' THEN 4 WHEN 'mayo' THEN 5 WHEN 'junio' THEN 6 WHEN 'julio' THEN 7 WHEN 'agosto' THEN 8 WHEN 'septiembre' THEN 9 WHEN 'setiembre' THEN 9 WHEN 'octubre' THEN 10 WHEN 'noviembre' THEN 11 WHEN 'diciembre' THEN 12\n"
        "    END\n"
        "  ELSE NULL\n"
        "END"
    )
    CASE_YEAR_TO_INT = (
        "CASE\n"
        "  WHEN NULLIF(TRIM((anio)::text),'') ~ '^[0-9]{1,4}$' THEN (NULLIF(TRIM((anio)::text),'')::int)\n"
        "  ELSE NULL\n"
        "END"
    )

    logger = logging.getLogger('coofisam')

    if request.method in ('POST', 'PUT'):
        data = request.data
        nombre = (data.get('nombre_indicador') or data.get('indicador') or '').strip()
        if not nombre:
            return Response({'error': 'nombre_indicador/indicador es requerido'}, status=400)
        try:
            anio = int(data.get('anio'))
            mes = int(data.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes deben ser enteros'}, status=400)
        alcance = (data.get('alcance') or data.get('descripcion') or data.get('scope') or '').strip() or None
        def _num(v):
            if v in (None, ''):
                return None
            try:
                return float(v)
            except Exception:
                try:
                    return float(str(v).replace(',', '.'))
                except Exception:
                    return None
        v_actual = _num(data.get('mesActual') or data.get('mes_actual') or data.get('valor_indicador'))
        v_dic = _num(data.get('diciembre1a') or data.get('anio_pasado_diciembre') or data.get('anio_menos_1_dic') or data.get('mes_de_diciembre_fijo'))
        v_1a = _num(data.get('mes1a') or data.get('mismo_mes_1_anio') or data.get('valor_indicador_2'))
        v_2a = _num(data.get('mes2a') or data.get('mismo_mes_2_anio') or data.get('valor_indicador_3'))
        analisis_raw = data.get('analisis')
        analisis = None
        if analisis_raw is not None:
            analisis_stripped = str(analisis_raw).strip()
            analisis = analisis_stripped if analisis_stripped else None
        periodo_str = (data.get('periodo') or f"{anio:04d}-{mes:02d}").strip()[:7]

        try:
            with connections['default'].cursor() as c:
                # Si PUT con id -> actualizar por id
                rec_id = None
                try:
                    rec_id = int(data.get('id')) if data.get('id') is not None else None
                except Exception:
                    rec_id = None

                if rec_id is not None and request.method == 'PUT':
                    c.execute(
                        """
                        UPDATE finanzas.indicadores_comparativa
                        SET indicador = COALESCE(%s, indicador),
                            anio = COALESCE(%s, anio),
                            mes = COALESCE(%s, mes),
                            alcance = %s,
                            mes_actual = %s,
                            anio_pasado_diciembre = %s,
                            mismo_mes_1_anio = %s,
                            mismo_mes_2_anio = %s,
                            analisis = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        [
                            nombre or None,
                            anio,
                            mes,
                            alcance,
                            v_actual,
                            v_dic,
                            v_1a,
                            v_2a,
                            analisis,
                            rec_id,
                        ],
                    )
                    updated = c.rowcount
                else:
                    # Update por (indicador, anio, mes)
                    c.execute(
                        """
                        UPDATE finanzas.indicadores_comparativa
                        SET alcance = COALESCE(%s, alcance),
                            mes_actual = COALESCE(%s, mes_actual),
                            anio_pasado_diciembre = COALESCE(%s, anio_pasado_diciembre),
                            mismo_mes_1_anio = COALESCE(%s, mismo_mes_1_anio),
                            mismo_mes_2_anio = COALESCE(%s, mismo_mes_2_anio),
                            analisis = COALESCE(%s, analisis),
                            updated_at = NOW()
                        WHERE lower(TRIM(indicador)) = lower(TRIM(%s))
                          AND anio = %s AND mes = %s
                        """,
                        [
                            alcance,
                            v_actual,
                            v_dic,
                            v_1a,
                            v_2a,
                            analisis,
                            nombre,
                            anio,
                            mes,
                        ],
                    )
                    updated = c.rowcount

                    if updated == 0 and request.method == 'POST':
                        # Insert nuevo
                        c.execute(
                            """
                            INSERT INTO finanzas.indicadores_comparativa (
                                indicador, anio, mes, alcance,
                                mes_actual, anio_pasado_diciembre, mismo_mes_1_anio, mismo_mes_2_anio, analisis,
                                created_at, updated_at
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                            RETURNING id
                            """,
                            [
                                nombre,
                                anio,
                                mes,
                                alcance,
                                v_actual,
                                v_dic,
                                v_1a,
                                v_2a,
                                analisis,
                            ],
                        )
                        row = c.fetchone()
                        new_id = row[0] if row else None
                        return Response({'success': True, 'created': True, 'id': new_id}, status=201)

            return Response({'success': True, 'updated_rows': updated})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    elif request.method == 'DELETE':
        # DELETE: Eliminar indicador por nombre, año y mes
        try:
            nombre = request.query_params.get('indicador') or request.query_params.get('nombre_indicador')
            year = request.query_params.get('year') or request.query_params.get('anio')
            month = request.query_params.get('month') or request.query_params.get('mes')
            
            if not nombre or not year or not month:
                return Response({'error': 'Se requiere indicador, año y mes para eliminar'}, status=400)
            
            try:
                anio = int(year)
                mes = int(month)
            except ValueError:
                return Response({'error': 'Año y mes deben ser números enteros'}, status=400)
            
            logger = logging.getLogger('coofisam')
            
            with connections['default'].cursor() as cursor:
                # Verificar que el registro existe
                cursor.execute("""
                    SELECT indicador, anio, mes
                    FROM finanzas.indicadores_comparativa
                    WHERE indicador = %s AND anio = %s AND mes = %s
                """, [nombre, anio, mes])
                
                existing = cursor.fetchone()
                if not existing:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                
                # Eliminar el registro
                cursor.execute("""
                    DELETE FROM finanzas.indicadores_comparativa
                    WHERE indicador = %s AND anio = %s AND mes = %s
                """, [nombre, anio, mes])
                
                logger.info(f"[finanzas.ic] Eliminado registro: {nombre} ({anio}-{mes})")
                
            return Response({'success': True, 'message': f'Indicador eliminado: {nombre} ({anio}-{mes})'})
            
        except Exception as e:
            logger = logging.getLogger('coofisam')
            logger.exception(f"[indicadores_comparativa] ERROR DELETE: {str(e)}")
            return Response({'error': str(e)}, status=500)

    # GET simple directo desde finanzas.indicadores_comparativa
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    indicador_q = request.query_params.get('indicador') or request.query_params.get('nombre_indicador')
    limit = int(request.query_params.get('limit') or '1000')

    where = []
    params = {}
    if year:
        where.append('f.anio = %(anio)s::int')
        params['anio'] = year
    if month:
        where.append('f.mes = %(mes)s::int')
        params['mes'] = month
    if indicador_q:
        where.append('lower(f.indicador) LIKE lower(%(ind)s)')
        params['ind'] = f"%{indicador_q}%"
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    sql = f"""
        WITH canon AS (
            SELECT DISTINCT nombre_indicador, alcance
            FROM indicadores.indicadores_financieros_comparativa
        )
        SELECT 
            f.id,
            CASE
              WHEN f.indicador ~ '[ÃÂ]' THEN convert_from(convert_to(f.indicador, 'LATIN1'), 'UTF8')
              WHEN f.indicador LIKE '%�%' THEN COALESCE(c_best.nombre_indicador, f.indicador)
              WHEN lower(regexp_replace(unaccent(f.indicador), '\\s+', ' ', 'g')) =
                   lower(regexp_replace(unaccent(COALESCE(c_best.nombre_indicador,'')), '\\s+', ' ', 'g'))
                THEN COALESCE(c_best.nombre_indicador, f.indicador)
              ELSE f.indicador
            END AS indicador,
            CASE 
              WHEN lower(COALESCE(c_best.nombre_indicador, f.indicador)) IN ('porcentaje endeudamiento','endeudamiento porcentaje','endeudamiento') THEN 'Total Pasivo – (Fondos sociales + Depósitos) / Total Activo'
              ELSE (
                CASE 
                  WHEN f.alcance ~ '[ÃÂ]' THEN convert_from(convert_to(f.alcance, 'LATIN1'), 'UTF8')
                  WHEN f.alcance LIKE '%�%' THEN COALESCE(c_best.alcance, f.alcance)
                  WHEN lower(regexp_replace(unaccent(COALESCE(f.alcance,'')), '\\s+', ' ', 'g')) =
                       lower(regexp_replace(unaccent(COALESCE(c_best.alcance,'')), '\\s+', ' ', 'g'))
                    THEN COALESCE(c_best.alcance, f.alcance)
                  ELSE f.alcance
                END
              )
            END AS alcance,
            f.anio,
            f.mes,
            f.periodo,
            COALESCE(f.mes_actual, 0) AS mes_actual,
            COALESCE(f.anio_pasado_diciembre, 0) AS anio_pasado_diciembre,
            COALESCE(f.mismo_mes_1_anio, 0) AS mismo_mes_1_anio,
            COALESCE(f.mismo_mes_2_anio, 0) AS mismo_mes_2_anio,
            COALESCE(
              CASE 
                WHEN f.analisis ~ '[ÃÂ]' THEN convert_from(convert_to(f.analisis, 'LATIN1'), 'UTF8')
                WHEN f.analisis LIKE '%�%' THEN NULL
                ELSE f.analisis
              END,
              ii.interpretacion,
              ''
            ) AS analisis
        FROM finanzas.indicadores_comparativa f
        LEFT JOIN LATERAL (
            SELECT c.nombre_indicador, c.alcance
            FROM canon c
            CROSS JOIN LATERAL (
                SELECT 
                  lower(regexp_replace(unaccent(c.nombre_indicador), '\\s+', ' ', 'g'))  AS nc,
                  lower(regexp_replace(unaccent(f.indicador),         '\\s+', ' ', 'g'))  AS nf
            ) norm
            ORDER BY 
              CASE 
                WHEN norm.nc = norm.nf THEN 0
                WHEN position(norm.nf in norm.nc) > 0 THEN 1
                WHEN position(norm.nc in norm.nf) > 0 THEN 2
                ELSE 3
              END,
              abs(length(norm.nc) - length(norm.nf))
            LIMIT 1
        ) c_best ON TRUE
        LEFT JOIN indicadores_interpretacion ii
          ON ii.anio = f.anio AND ii.mes = f.mes
         AND (
              (c_best.nombre_indicador IS NOT NULL AND ii.indicador = c_best.nombre_indicador)
              OR (c_best.nombre_indicador IS NULL AND ii.indicador = f.indicador)
         )
        {where_sql}
        ORDER BY indicador, anio DESC, mes DESC
        LIMIT {limit}
    """
    try:
        with connections['default'].cursor() as c:
            if params:
                _exec(c, sql, params)
            else:
                c.execute(sql)
            cols = [col[0] for col in c.description]
            rows = [dict(zip(cols, row)) for row in c.fetchall()]
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    # Normalizar al shape del front
    from hashlib import md5
    items = []
    for r in rows:
        y = int(r.get('anio') or 0)
        m = int(r.get('mes') or 0)
        name = _fix_encoding(r.get('indicador') or '') or ''
        _id = md5(f"{name}|{y}|{m}".encode()).hexdigest()[:16]
        periodo_val = (r.get('periodo') or f"{y:04d}-{m:02d}").strip()
        items.append({
            'id': _id,
            'fecha': f"{periodo_val}-01",
            'anio': y,
            'mes': m,
            'periodo': periodo_val,
            'indicador': name,
            'alcance': _fix_encoding(r.get('alcance')),
            'mesActual': r.get('mes_actual'),
            'diciembre1a': r.get('anio_pasado_diciembre'),
            'mes1a': r.get('mismo_mes_1_anio'),
            'mes2a': r.get('mismo_mes_2_anio'),
            'analisis': _fix_encoding(r.get('analisis') or '') or '',
        })

    return Response({'items': items, 'count': len(items), 'filters': {'year': year, 'month': month, 'indicador': indicador_q}})


# ====== Oficinas (finanzas.oficinas_mes) ======

"""
*********************************************
*       Categorías de Oficinas (CRUD)        *
*********************************************
+-----------------------------------+
|        Función de inicio          |
|-----------------------------------|
| Endpoints GET/POST/DELETE para    |
| finanzas.oficinas                 |
+-----------------------------------+
"""
class OficinasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year') or request.query_params.get('anio')
        month = request.query_params.get('month') or request.query_params.get('mes')
        q = request.query_params.get('q') or request.query_params.get('search') or request.query_params.get('indicador')
        limit = int(request.query_params.get('limit') or '500')

        logger = logging.getLogger('coofisam')

        try:
            year_int = int(str(year)) if year not in (None, '') else None
        except Exception:
            year_int = None
        try:
            month_int = int(str(month)) if month not in (None, '') else None
        except Exception:
            month_int = None

        where = []
        params = {}
        if year:
            where.append('anio = %(anio)s::int')
            params['anio'] = year
        if month:
            where.append('mes = %(mes)s::int')
            params['mes'] = month
        if q:
            where.append('(lower(codigo) LIKE lower(%(q)s) OR lower(nombre) LIKE lower(%(q)s))')
            params['q'] = f"%{q}%"
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

        _ensure_indicadores_comparativa_table()

        if year_int is not None and month_int is not None:
            try:
                _refresh_oficina_saldos(year_int, month_int, None, logger)
            except Exception:
                logger.exception('[oficinas] No se pudo refrescar saldos antes del listado')

        sql = f"""
            WITH base AS (
              SELECT
                codigo::text AS codigo,
                CASE
                  WHEN NULLIF(codigo::text, '') ~ '^[0-9]+' THEN NULLIF(codigo::text, '')::int
                  ELSE NULL
                END AS codigo_num,
                nombre::text AS nombre,
                anio::int AS anio,
                mes::int AS mes,
                CASE mes
                  WHEN 1 THEN 'Enero'
                  WHEN 2 THEN 'Febrero'
                  WHEN 3 THEN 'Marzo'
                  WHEN 4 THEN 'Abril'
                  WHEN 5 THEN 'Mayo'
                  WHEN 6 THEN 'Junio'
                  WHEN 7 THEN 'Julio'
                  WHEN 8 THEN 'Agosto'
                  WHEN 9 THEN 'Septiembre'
                  WHEN 10 THEN 'Octubre'
                  WHEN 11 THEN 'Noviembre'
                  WHEN 12 THEN 'Diciembre'
                  ELSE ''
                END AS mes_nombre,
                COALESCE(
                  o.fecha_apertura::date,
                  (SELECT MIN(fo.fecha_apertura) FROM finanzas.oficinas fo WHERE fo.codigo = o.codigo)
                ) AS fecha,
                COALESCE(asociados,0)::int AS asociados,
                COALESCE(entidades_financieras,0)::int AS entidades,
                COALESCE(poblacion,0)::int AS poblacion,
                COALESCE(cta_puc_14::numeric,0)::numeric AS cartera_credito,
                COALESCE(cta_puc_21::numeric,0)::numeric AS depositos
              FROM finanzas.oficinas o
              {where_sql}
              ORDER BY codigo, anio DESC, mes DESC
              LIMIT {limit}
            )
            SELECT
              b.codigo,
              b.nombre,
              b.anio,
              b.mes,
              b.mes_nombre,
              b.fecha,
              b.asociados,
              b.entidades,
              b.poblacion,
              b.cartera_credito,
              b.depositos,
              b.cartera_credito AS saldo_c14,
              b.depositos AS saldo_c21
            FROM base b
            ORDER BY b.codigo, b.anio DESC, b.mes DESC
        """
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            rows = [dict(zip(cols, row)) for row in c.fetchall()]

        # Mapear al shape que el front espera
        def map_row(r):
            from hashlib import md5
            _id = md5(f"{r['codigo']}|{r['anio']}|{r['mes']}".encode()).hexdigest()[:16]
            return {
                'id': _id,
                'codigo': r['codigo'],
                'nombre': r['nombre'],
                'fecha': r['fecha'],
                'saldo_c14': r.get('saldo_c14') or 0,
                'saldo_c21': r.get('saldo_c21') or 0,
                'ctaPuc14': r.get('saldo_c14') or 0,
                'ctaPuc21': r.get('saldo_c21') or 0,
                'asociados': r['asociados'],
                'entidades': r['entidades'],
                'poblacion': r['poblacion'],
                'anio': r['anio'],
                'mes': r['mes'],
            }

        items = [map_row(r) for r in rows]
        return Response({'items': items, 'count': len(items), 'filters': {'year': year, 'month': month, 'q': q}})

    def post(self, request):
        data = request.data
        codigo = (data.get('codigo') or data.get('codigo_oficina') or '').strip()
        if not codigo:
            return Response({'error': 'codigo (codigo_oficina) es requerido'}, status=400)
        try:
            anio = int(data.get('anio') or data.get('year'))
            mes = int(data.get('mes') or data.get('month'))
        except Exception:
            return Response({'error': 'anio y mes (mes_num) son requeridos y deben ser enteros'}, status=400)

        nombre = (data.get('nombre') or data.get('nombre_oficina') or '').strip() or None
        fecha = data.get('fecha') or data.get('fecha_apertura') or None
        fecha = _to_iso_date(fecha)
        def to_int(x):
            try:
                return None if x in (None, '', '-') else int(str(x).replace(',', ''))
            except Exception:
                return None
        asociados = to_int(data.get('asociados'))
        entidades = to_int(data.get('entidades') or data.get('entidades_financieras'))
        poblacion = to_int(data.get('poblacion'))

        with connections['default'].cursor() as c:
            # Intentar UPDATE primero (no permitir modificar fecha_apertura)
            c.execute(
                """
                UPDATE finanzas.oficinas
                SET nombre = COALESCE(%s, nombre),
                    asociados = COALESCE(%s, asociados),
                    entidades_financieras = COALESCE(%s, entidades_financieras),
                    poblacion = COALESCE(%s, poblacion),
                    updated_at = NOW()
                WHERE codigo = %s AND anio = %s AND mes = %s
                """,
                [nombre, asociados, entidades, poblacion, codigo, anio, mes]
            )
            if c.rowcount == 0:
                # INSERT si no existe registro para (codigo, anio, mes)
                # Primero obtener el oficina_id
                c.execute("SELECT oficina_id FROM finanzas.org_oficina WHERE codigo = %s", [codigo])
                oficina_result = c.fetchone()
                if not oficina_result:
                    return Response({'error': f'Oficina con código {codigo} no encontrada en org_oficina'}, status=400)
                oficina_id = oficina_result[0]
                
                c.execute(
                    """
                    INSERT INTO finanzas.oficinas
                    (oficina_id, codigo, nombre, anio, mes, fecha_apertura, asociados, entidades_financieras, poblacion)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [oficina_id, codigo, nombre or '', anio, mes, fecha, asociados, entidades, poblacion]
                )

        return Response({'success': True, 'saved': {'codigo': codigo, 'anio': anio, 'mes': mes}})


"""
-------------------------------------
 Detalle de Oficina (por código)
-------------------------------------
"""
class OficinaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo: str):
        year = request.query_params.get('year') or request.query_params.get('anio')
        month = request.query_params.get('month') or request.query_params.get('mes')
        where = ['codigo = %(codigo)s']
        params = {'codigo': codigo}
        if year:
            where.append('anio = %(anio)s::int')
            params['anio'] = year
        if month:
            where.append('mes = %(mes)s::int')
            params['mes'] = month
        where_sql = ' AND '.join(where)

        _ensure_indicadores_comparativa_table()

        logger = logging.getLogger('coofisam')
        try:
            year_int = int(str(year)) if year not in (None, '') else None
        except Exception:
            year_int = None
        try:
            month_int = int(str(month)) if month not in (None, '') else None
        except Exception:
            month_int = None
        try:
            codigo_int = int(str(codigo)) if codigo not in (None, '') else None
        except Exception:
            codigo_int = None

        if year_int is not None and month_int is not None and codigo_int is not None:
            try:
                _refresh_oficina_saldos(year_int, month_int, codigo_int, logger)
            except Exception:
                logger.exception('[oficina] No se pudo refrescar saldos antes de la consulta puntual')

        # Primera consulta: período exacto (si se envía year/month) o último registro si no
        sql_exact = f"""
            WITH base AS (
                SELECT
                  o.codigo::text AS codigo,
                  CASE
                    WHEN NULLIF(o.codigo::text, '') ~ '^[0-9]+' THEN NULLIF(o.codigo::text, '')::int
                    ELSE NULL
                  END AS codigo_num,
                  o.nombre::text AS nombre,
                  o.anio::int AS anio,
                  o.mes::int AS mes,
                  COALESCE(
                    o.fecha_apertura::date,
                    (SELECT MIN(fo.fecha_apertura) FROM finanzas.oficinas fo WHERE fo.codigo = o.codigo)
                  ) AS fecha,
                  COALESCE(o.asociados,0)::int AS asociados,
                  COALESCE(o.entidades_financieras,0)::int AS entidades,
                  COALESCE(o.poblacion,0)::int AS poblacion,
                  COALESCE(o.cta_puc_14::numeric,0)::numeric AS cartera_credito,
                  COALESCE(o.cta_puc_21::numeric,0)::numeric AS depositos
                FROM finanzas.oficinas o
                WHERE {where_sql}
                ORDER BY anio DESC, mes DESC
                LIMIT 1
            )
            SELECT
              b.codigo,
              b.nombre,
              b.anio,
              b.mes,
              b.fecha,
              b.asociados,
              b.entidades,
              b.poblacion,
              b.cartera_credito AS saldo_c14,
              b.depositos AS saldo_c21
            FROM base b
        """

        # Consulta fallback: último registro anterior al período solicitado
        sql_prev = None
        params_prev = params.copy()
        if year and month:
            sql_prev = """
                WITH base AS (
                    SELECT
                      o.codigo::text AS codigo,
                      CASE
                        WHEN NULLIF(o.codigo::text, '') ~ '^[0-9]+' THEN NULLIF(o.codigo::text, '')::int
                        ELSE NULL
                      END AS codigo_num,
                      o.nombre::text AS nombre,
                      o.anio::int AS anio,
                      o.mes::int AS mes,
                      COALESCE(
                        o.fecha_apertura::date,
                        (SELECT MIN(fo.fecha_apertura) FROM finanzas.oficinas fo WHERE fo.codigo = o.codigo)
                      ) AS fecha,
                      COALESCE(o.asociados,0)::int AS asociados,
                      COALESCE(o.entidades_financieras,0)::int AS entidades,
                      COALESCE(o.poblacion,0)::int AS poblacion,
                      COALESCE(o.cta_puc_14::numeric,0)::numeric AS cartera_credito,
                      COALESCE(o.cta_puc_21::numeric,0)::numeric AS depositos
                    FROM finanzas.oficinas o
                    WHERE codigo = %(codigo)s AND (anio < %(anio)s::int OR (anio = %(anio)s::int AND mes < %(mes)s::int))
                    ORDER BY anio DESC, mes DESC
                    LIMIT 1
                )
                SELECT
                  b.codigo,
                  b.nombre,
                  b.anio,
                  b.mes,
                  b.fecha,
                  b.asociados,
                  b.entidades,
                  b.poblacion,
                  b.cartera_credito AS saldo_c14,
                  b.depositos AS saldo_c21
                FROM base b
            """

        with connections['default'].cursor() as c:
            _exec(c, sql_exact, params)
            row = c.fetchone()
            if not row and sql_prev:
                _exec(c, sql_prev, params_prev)
                row = c.fetchone()
            if not row:
                return Response({'error': 'Oficina no encontrada'}, status=404)
            cols = [col[0] for col in c.description]
            r = dict(zip(cols, row))
        r['id'] = r.get('codigo')
        r['saldo_c14'] = r.get('saldo_c14') or 0
        r['saldo_c21'] = r.get('saldo_c21') or 0
        r['ctaPuc14'] = r['saldo_c14']
        r['ctaPuc21'] = r['saldo_c21']
        return Response(r)

    def delete(self, request, codigo: str):
        """
        DELETE: Eliminar registro de oficina para (codigo, anio, mes)
        - Fuente de datos principal: finanzas.oficinas
        - Limpia también finanzas.oficinas_mes si existe la fila
        """
        try:
            year = request.query_params.get('year') or request.query_params.get('anio')
            month = request.query_params.get('month') or request.query_params.get('mes')
            if not year or not month:
                return Response({'error': 'Se requiere año y mes para eliminar'}, status=400)
            try:
                anio = int(year)
                mes = int(month)
            except ValueError:
                return Response({'error': 'Año y mes deben ser números enteros'}, status=400)

            logger = logging.getLogger('coofisam')
            with connections['default'].cursor() as cursor:
                # Verificar en la tabla origen usada por el listado/POST
                cursor.execute(
                    """
                    SELECT codigo, nombre, anio, mes
                    FROM finanzas.oficinas
                    WHERE codigo = %s AND anio = %s AND mes = %s
                    """,
                    [codigo, anio, mes]
                )
                existing = cursor.fetchone()
                if not existing:
                    return Response({'error': 'Registro no encontrado'}, status=404)

                # Borrar del origen
                cursor.execute(
                    """
                    DELETE FROM finanzas.oficinas
                    WHERE codigo = %s AND anio = %s AND mes = %s
                    """,
                    [codigo, anio, mes]
                )

                # Intentar limpiar también en la tabla mensual si estuviera poblada
                try:
                    cursor.execute(
                        """
                        DELETE FROM finanzas.oficinas_mes
                        WHERE codigo_oficina = %s AND anio = %s AND mes_num = %s
                        """,
                        [codigo, anio, mes]
                    )
                except Exception:
                    # No es crítico si no existe la tabla/registro
                    pass

                logger.info(f"[oficina] Eliminado registro finanzas.oficinas: {codigo} ({anio}-{mes})")

            return Response({'success': True, 'message': f'Registro eliminado: {codigo} ({anio}-{mes})'})

        except Exception as e:
            logger = logging.getLogger('coofisam')
            logger.exception(f"[oficina] ERROR DELETE: {str(e)}")
            return Response({'error': str(e)}, status=500)


"""
*********************************************
*     Análisis Explicativo (CRUD simple)     *
*********************************************
"""
class AnalisisExplicativoView(APIView):
    """
    API para gestionar análisis explicativo financiero
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtener análisis explicativo
        """
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        categoria = request.query_params.get('categoria')
        limit = int(request.query_params.get('limit') or '500')
        
        where = []
        params = {}
        
        if year:
            where.append("anio = %(anio)s")
            params['anio'] = int(year)
            logger.info(f"[analisis_explicativo] Filtro por año: {year}")
            
        if month:
            where.append("mes = %(mes)s")
            params['mes'] = month
            logger.info(f"[analisis_explicativo] Filtro por mes: {month}")
            
        if categoria:
            where.append('lower(trim(categoria)) LIKE lower(trim(%(categoria)s))')
            params['categoria'] = f"%{categoria}%"
            
        where_sql = (' AND ' + ' AND '.join(where)) if where else ''
        
        sql = f"""
            SELECT 
                id,
                anio,
                mes,
                categoria,
                subcategoria,
                descripcion,
                created_at,
                updated_at
            FROM finanzas.analisis_explicativo
            WHERE 1=1 {where_sql}
            ORDER BY anio DESC, mes DESC, categoria, subcategoria
            LIMIT {limit}
        """
        
        try:
            with connections['default'].cursor() as c:
                _exec(c, sql, params)
                cols = [col[0] for col in c.description]
                rows = [dict(zip(cols, row)) for row in c.fetchall()]
        except Exception as e:
            msg = str(e)
            logger.exception(f"[analisis_explicativo] ERROR GET: {msg}")
            return Response({'error': msg}, status=500)
        
        # Normalizar al shape que espera el front
        items = []
        for r in rows:
            items.append({
                'id': r.get('id'),
                'anio': r.get('anio'),
                'mes': r.get('mes'),
                'categoria': r.get('categoria'),
                'subcategoria': r.get('subcategoria'),
                'descripcion': r.get('descripcion') or '',
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
            })
        
        return Response({
            'items': items,
            'count': len(items),
            'filters': {
                'year': year,
                'month': month,
                'categoria': categoria,
                'limit': limit
            }
        })

    def post(self, request):
        """
        Crear o actualizar análisis explicativo
        """
        try:
            data = request.data
            
            # Validar datos requeridos
            if not data.get('categoria'):
                return Response({'error': 'Categoría es requerida'}, status=400)
            if not data.get('anio'):
                return Response({'error': 'Año es requerido'}, status=400)
            if not data.get('mes'):
                return Response({'error': 'Mes es requerido'}, status=400)
            if not data.get('subcategoria'):
                return Response({'error': 'Subcategoría es requerida'}, status=400)
            
            categoria = data['categoria']
            anio = int(data['anio'])
            mes = data['mes']
            mes_num = data.get('mes_num')
            if not mes_num:
                # Mapear nombre del mes a número
                meses = {
                    'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
                    'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
                    'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
                }
                mes_num = meses.get(mes, 1)
            else:
                mes_num = int(mes_num)
            subcategoria = data['subcategoria']
            descripcion = data.get('descripcion', '')
            
            # Verificar si ya existe un registro
            with connections['default'].cursor() as c:
                c.execute("""
                    SELECT id FROM finanzas.analisis_explicativo
                    WHERE anio = %s AND mes = %s AND categoria = %s AND subcategoria = %s
                """, [anio, mes, categoria, subcategoria])
                existing = c.fetchone()
                
                if existing:
                    # Actualizar registro existente
                    c.execute("""
                        UPDATE finanzas.analisis_explicativo
                        SET descripcion = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, [descripcion, existing[0]])
                    logger.info(f"[analisis_explicativo] Actualizado registro ID: {existing[0]}")
                else:
                    # Crear nuevo registro
                    c.execute("""
                        INSERT INTO finanzas.analisis_explicativo
                        (anio, mes, mes_num, categoria, subcategoria, descripcion)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [anio, mes, mes_num, categoria, subcategoria, descripcion])
                    logger.info(f"[analisis_explicativo] Creado nuevo registro para {categoria} - {subcategoria} {anio}-{mes}")
            
            return Response({'message': 'Análisis guardado correctamente'}, status=200)
            
        except Exception as e:
            msg = str(e)
            logger.exception(f"[analisis_explicativo] ERROR POST: {msg}")
            return Response({'error': msg}, status=500)

    def put(self, request, id=None):
        """
        Actualizar análisis explicativo por ID
        """
        try:
            if not id:
                return Response({'error': 'ID es requerido'}, status=400)
                
            data = request.data
            
            # Validar datos requeridos
            if not data.get('categoria'):
                return Response({'error': 'Categoría es requerida'}, status=400)
            if not data.get('anio'):
                return Response({'error': 'Año es requerido'}, status=400)
            if not data.get('mes'):
                return Response({'error': 'Mes es requerido'}, status=400)
            if not data.get('subcategoria'):
                return Response({'error': 'Subcategoría es requerida'}, status=400)
            
            categoria = data['categoria']
            anio = int(data['anio'])
            mes = data['mes']
            mes_num = data.get('mes_num')
            if not mes_num:
                # Mapear nombre del mes a número
                meses = {
                    'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
                    'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
                    'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
                }
                mes_num = meses.get(mes, 1)
            else:
                mes_num = int(mes_num)
            subcategoria = data['subcategoria']
            descripcion = data.get('descripcion', '')
            
            # Verificar si el registro existe
            with connections['default'].cursor() as c:
                c.execute("""
                    SELECT id FROM finanzas.analisis_explicativo
                    WHERE id = %s
                """, [id])
                existing = c.fetchone()
                
                if not existing:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                
                # Actualizar registro existente
                c.execute("""
                    UPDATE finanzas.analisis_explicativo
                    SET anio = %s, mes = %s, mes_num = %s, categoria = %s, 
                        subcategoria = %s, descripcion = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, [anio, mes, mes_num, categoria, subcategoria, descripcion, id])
                logger.info(f"[analisis_explicativo] Actualizado registro ID: {id}")
            
            return Response({'message': 'Análisis actualizado correctamente'}, status=200)
            
        except Exception as e:
            msg = str(e)
            logger.exception(f"[analisis_explicativo] ERROR PUT: {msg}")
            return Response({'error': msg}, status=500)

    def delete(self, request, id=None):
        """
        Eliminar análisis explicativo
        """
        try:
            if not id:
                return Response({'error': 'ID es requerido'}, status=400)
            
            # Verificar si el registro existe
            with connections['default'].cursor() as c:
                c.execute("""
                    SELECT id FROM finanzas.analisis_explicativo
                    WHERE id = %s
                """, [id])
                existing = c.fetchone()
                
                if not existing:
                    return Response({'error': 'Análisis no encontrado'}, status=404)
                
                # Eliminar el registro
                c.execute("""
                    DELETE FROM finanzas.analisis_explicativo
                    WHERE id = %s
                """, [id])
                logger.info(f"[analisis_explicativo] Eliminado registro ID: {id}")
            
            return Response({'message': 'Análisis eliminado correctamente'}, status=200)
            
        except Exception as e:
            msg = str(e)
            logger.exception(f"[analisis_explicativo] ERROR DELETE: {msg}")
            return Response({'error': msg}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def indicadores_disponibles(request):
    """GET: Lista todos los indicadores disponibles con sus alcances"""
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT nombre_indicador, alcance 
                FROM indicadores.indicadores_financieros_comparativa 
                WHERE nombre_indicador IS NOT NULL 
                ORDER BY nombre_indicador
            """)
            
            indicadores = []
            for row in cursor.fetchall():
                nombre = _fix_encoding(row[0])
                alcance = _fix_encoding(row[1]) if row[1] is not None else ''
                indicadores.append({
                    'nombre': nombre,
                    'alcance': alcance
                })
            
            return Response({'indicadores': indicadores}, status=200)
            
    except Exception as e:
        logger.exception(f"[indicadores_disponibles] ERROR: {str(e)}")
        return Response({'error': str(e)}, status=500)


"""
-------------------------------------
 Catálogo de oficinas disponibles
-------------------------------------
"""
@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Temporalmente sin autenticación para pruebas
def oficinas_disponibles(request):
    """
    Retorna una lista de todas las oficinas disponibles (código y nombre)
    desde la tabla finanzas.org_oficina.
    """
    try:
        with connections['default'].cursor() as c:
            c.execute("""
                SELECT
                    codigo::text AS codigo,
                    nombre::text AS nombre
                FROM finanzas.org_oficina
                ORDER BY codigo::int
            """)
            cols = [col[0] for col in c.description]
            oficinas = [dict(zip(cols, row)) for row in c.fetchall()]
        return Response({'oficinas': oficinas})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


"""
*********************************************
*   Ejecución Presupuestal PUC6 (CRUD)       *
*********************************************
"""
class EjecucionPresupuestalView(APIView):
    """
    Vista para gestionar Ejecución Presupuestal PUC 6 dígitos
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET: Lista todos los registros de ejecución presupuestal
        """
        try:
            # Parámetros de filtro
            anio = request.GET.get('anio')
            mes = request.GET.get('mes')
            codigo_puc6 = request.GET.get('codigo_puc6')
            limit = int(request.GET.get('limit', 1000))
            offset = int(request.GET.get('offset', 0))
            
            # Construir query base
            query = """
                SELECT 
                    id, anio, mes, codigo_puc6, nombre_rubro,
                    proyectado, historico, diff_abs, diff_pct, periodo, created_at
                FROM finanzas.ejecucion_presupuestal
                WHERE 1=1
            """
            params = []
            
            # Aplicar filtros
            if anio:
                query += " AND anio = %s"
                params.append(anio)
            if mes:
                query += " AND mes = %s"
                params.append(mes)
            if codigo_puc6:
                query += " AND codigo_puc6 ILIKE %s"
                params.append(f'%{codigo_puc6}%')
            
            # Ordenamiento y paginación
            query += " ORDER BY anio DESC, mes DESC, codigo_puc6"
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            with connections['default'].cursor() as cursor:
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    item = dict(zip(columns, row))
                    # Convertir decimales a float para JSON
                    for key in ['proyectado', 'historico', 'diff_abs', 'diff_pct']:
                        if item[key] is not None:
                            item[key] = float(item[key])
                    items.append(item)
                
                # Contar total de registros
                count_query = """
                    SELECT COUNT(*) FROM finanzas.ejecucion_presupuestal WHERE 1=1
                """
                count_params = []
                if anio:
                    count_query += " AND anio = %s"
                    count_params.append(anio)
                if mes:
                    count_query += " AND mes = %s"
                    count_params.append(mes)
                if codigo_puc6:
                    count_query += " AND codigo_puc6 ILIKE %s"
                    count_params.append(f'%{codigo_puc6}%')
                
                cursor.execute(count_query, count_params)
                total_count = cursor.fetchone()[0]
                
                return Response({
                    'items': items,
                    'count': total_count,
                    'filters': {
                        'anio': anio,
                        'mes': mes,
                        'codigo_puc6': codigo_puc6
                    }
                }, status=200)
                
        except Exception as e:
            logger.exception(f"[ejecucion_presupuestal] ERROR GET: {str(e)}")
            return Response({'error': str(e)}, status=500)

    def post(self, request):
        """
        POST: Crear o actualizar registro de ejecución presupuestal
        """
        try:
            data = request.data
            
            # Validar campos requeridos
            if not data.get('anio'):
                return Response({'error': 'Año es requerido'}, status=400)
            if not data.get('mes'):
                return Response({'error': 'Mes es requerido'}, status=400)
            if not data.get('codigo_puc6'):
                return Response({'error': 'Código PUC 6 dígitos es requerido'}, status=400)
            if not data.get('nombre_rubro'):
                return Response({'error': 'Nombre del rubro es requerido'}, status=400)
            
            anio = int(data['anio'])
            mes = int(data['mes'])
            codigo_puc6 = data['codigo_puc6'].strip()
            nombre_rubro = data['nombre_rubro'].strip()
            proyectado = data.get('proyectado')
            historico = data.get('historico')
            
            # Validar que el código PUC tenga exactamente 6 dígitos
            if len(codigo_puc6) != 6 or not codigo_puc6.isdigit():
                return Response({'error': 'El código PUC debe tener exactamente 6 dígitos'}, status=400)
            
            # Validar mes
            if mes < 1 or mes > 12:
                return Response({'error': 'El mes debe estar entre 1 y 12'}, status=400)
            
            # Convertir valores numéricos
            if proyectado is not None and proyectado != '':
                try:
                    proyectado = float(proyectado)
                except (ValueError, TypeError):
                    proyectado = None
            
            if historico is not None and historico != '':
                try:
                    historico = float(historico)
                except (ValueError, TypeError):
                    historico = None
            
            with connections['default'].cursor() as cursor:
                # Verificar si ya existe un registro
                cursor.execute("""
                    SELECT id FROM finanzas.ejecucion_presupuestal
                    WHERE anio = %s AND mes = %s AND codigo_puc6 = %s
                """, [anio, mes, codigo_puc6])
                existing = cursor.fetchone()
                
                if existing:
                    # Actualizar registro existente
                    cursor.execute("""
                        UPDATE finanzas.ejecucion_presupuestal
                        SET nombre_rubro = %s, proyectado = %s, historico = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, [nombre_rubro, proyectado, historico, existing[0]])
                    logger.info(f"[ejecucion_presupuestal] Actualizado registro ID: {existing[0]}")
                    message = "Registro actualizado correctamente"
                else:
                    # Crear nuevo registro
                    cursor.execute("""
                        INSERT INTO finanzas.ejecucion_presupuestal
                        (anio, mes, codigo_puc6, nombre_rubro, proyectado, historico)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [anio, mes, codigo_puc6, nombre_rubro, proyectado, historico])
                    logger.info(f"[ejecucion_presupuestal] Creado nuevo registro para {codigo_puc6} {anio}-{mes}")
                    message = "Registro creado correctamente"
            
            return Response({'message': message}, status=200)
            
        except Exception as e:
            msg = str(e)
            logger.exception(f"[ejecucion_presupuestal] ERROR POST: {msg}")
            return Response({'error': msg}, status=500)

    def delete(self, request, id=None):
        """
        DELETE: Eliminar registro de ejecución presupuestal
        """
        try:
            if not id:
                return Response({'error': 'ID es requerido'}, status=400)
            
            with connections['default'].cursor() as cursor:
                # Verificar si el registro existe
                cursor.execute("""
                    SELECT id, codigo_puc6, anio, mes FROM finanzas.ejecucion_presupuestal
                    WHERE id = %s
                """, [id])
                existing = cursor.fetchone()
                
                if not existing:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                
                # Eliminar el registro
                cursor.execute("""
                    DELETE FROM finanzas.ejecucion_presupuestal
                    WHERE id = %s
                """, [id])
                logger.info(f"[ejecucion_presupuestal] Eliminado registro ID: {id} ({existing[1]} {existing[2]}-{existing[3]})")
            
            return Response({'message': 'Registro eliminado correctamente'}, status=200)
            
        except Exception as e:
            msg = str(e)
            logger.exception(f"[ejecucion_presupuestal] ERROR DELETE: {msg}")
            return Response({'error': msg}, status=500)


class EjecucionPresupuestalUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Carga masiva de ejecución presupuestal desde XLSX/CSV.
        Columnas esperadas (insensible a mayúsculas): codigo, denominación/denominacion, proyectado.
        Solo se insertan códigos de 6 dígitos. Año y mes vienen en el form (anio, mes).
        """
        f = request.FILES.get('file')
        if not f:
            return Response({'error': "Archivo 'file' requerido"}, status=400)
        try:
            anio = int(request.POST.get('anio'))
            mes = int(request.POST.get('mes'))
        except Exception:
            return Response({'error': 'anio y mes requeridos y numéricos'}, status=400)
        if not (1 <= mes <= 12):
            return Response({'error': 'mes inválido (1-12)'}, status=400)

        import io, csv, re
        content = f.read()

        # Guardar archivo bajo LIBRO_BALANCE_ROOT/EjecucionPresupuestal/Aanoo_<anio>/
        try:
            root = _get_balance_root()
            target_dir = root / 'EjecucionPresupuestal' / f'Aanoo_{anio}'
            target_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime as pydt
            ext = Path(getattr(f, 'name', 'upload.xlsx')).suffix or '.xlsx'
            safe_name = f"ejecucion_puc6_{anio}_{mes}_{pydt.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            dest_path = target_dir / safe_name
            with open(dest_path, 'wb+') as dst:
                dst.write(content)
        except Exception:
            pass

        def norm_num(x):
            if x in (None, ''):
                return None
            s = str(x)
            # remover miles y normalizar decimal
            s = s.replace('\u00a0',' ').replace(' ','').replace('.','')
            s = s.replace(',', '.')
            try:
                return float(s)
            except Exception:
                return None

        def norm_code(x):
            if x is None:
                return None
            s = re.sub(r'\D', '', str(x))
            return s if len(s) == 6 else None

        imported = 0
        errors = []

        def upsert_row(codigo6, denominacion, proyectado_val):
            with connections['default'].cursor() as c:
                c.execute(
                    """
                    SELECT id FROM finanzas.ejecucion_presupuestal
                    WHERE anio=%s AND mes=%s AND codigo_puc6=%s
                    """,
                    [anio, mes, codigo6]
                )
                row = c.fetchone()
                if row:
                    c.execute(
                        """
                        UPDATE finanzas.ejecucion_presupuestal
                        SET nombre_rubro=%s, proyectado=%s, updated_at = CURRENT_TIMESTAMP
                        WHERE id=%s
                        """,
                        [denominacion or '', proyectado_val, row[0]]
                    )
                else:
                    c.execute(
                        """
                        INSERT INTO finanzas.ejecucion_presupuestal (anio, mes, codigo_puc6, nombre_rubro, proyectado)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        [anio, mes, codigo6, denominacion or '', proyectado_val]
                    )

        try:
            filename = getattr(f, 'name', 'upload')
            if filename.lower().endswith('.csv'):
                text = content.decode('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(text))
                for i, row in enumerate(reader, 2):
                    # Normalize keys
                    lower = { (k or '').strip().lower(): v for k, v in row.items() }
                    # Buscar por tokens en encabezado
                    def find_by_tokens(d, tokens):
                        for key in d.keys():
                            if all(tok in key for tok in tokens):
                                return d.get(key)
                        return None
                    codigo_val = find_by_tokens(lower, ['codigo']) or lower.get('cuenta') or lower.get('codigo puc6') or lower.get('codigo_puc6')
                    codigo6 = norm_code(codigo_val)
                    denom = (find_by_tokens(lower, ['denomin']) or find_by_tokens(lower, ['nombre'])) or ''
                    proj_raw = (find_by_tokens(lower, ['proyect']) or lower.get('[a] proyectado') or lower.get('monto proyectado'))
                    if proj_raw is None:
                        # Fallback: si hay una columna 'monto' y no hay otra 'histor', tomarla
                        monto_keys = [k for k in lower.keys() if 'monto' in k]
                        hist_keys = [k for k in lower.keys() if 'hist' in k]
                        if len(monto_keys) == 1 and not hist_keys:
                            proj_raw = lower[monto_keys[0]]
                    proj = norm_num(proj_raw)
                    if not codigo6:
                        continue
                    upsert_row(codigo6, denom, proj)
                    imported += 1
            else:
                try:
                    import openpyxl
                except Exception:
                    return Response({'error': 'Para .xlsx se requiere openpyxl. Sube CSV o instala openpyxl.'}, status=400)
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                # Escanear primeras filas para detectar encabezados multi-fila
                max_scan_rows = min(6, ws.max_row)
                max_cols = ws.max_column
                col_texts = []
                for cidx in range(1, max_cols + 1):
                    parts = []
                    for ridx in range(1, max_scan_rows + 1):
                        v = ws.cell(ridx, cidx).value
                        if v is None:
                            continue
                        s = str(v).strip()
                        if s:
                            parts.append(s)
                    col_texts.append(' '.join(parts).lower())
                def find_idx(pred):
                    for idx, t in enumerate(col_texts):
                        try:
                            if pred(t):
                                return idx
                        except Exception:
                            pass
                    return None
                i_cod = find_idx(lambda t: 'código' in t or 'codigo' in t or 'cuenta' in t)
                i_den = find_idx(lambda t: 'denomin' in t or 'nombre' in t)
                i_pro = find_idx(lambda t: ('proyect' in t) and ('hist' not in t))
                if i_cod is None or i_den is None or i_pro is None:
                    return Response({'error': 'Encabezados requeridos: código, denominación y proyectado (pueden estar en encabezados múltiples).'}, status=400)
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    codigo6 = norm_code(row[i_cod] if i_cod is not None else None)
                    denom = (row[i_den] if i_den is not None else '') or ''
                    proj = norm_num(row[i_pro] if i_pro is not None else None)
                    if not codigo6:
                        continue
                    upsert_row(codigo6, denom, proj)
                    imported += 1
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({'success': True, 'imported': imported, 'errors': errors})


@api_view(['GET'])
@permission_classes([AllowAny])
def ejecucion_presupuestal_files(request):
    """Lista archivos subidos para Ejecución Presupuestal PUC6, agrupados por año."""
    year = request.query_params.get('year')
    root = _get_balance_root()
    base = root / 'EjecucionPresupuestal'
    out = []
    try:
        if not base.exists():
            return Response({'files': out})
        dirs = sorted([p for p in base.glob('Aanoo_*') if p.is_dir()])
        for d in dirs:
            y = d.name.replace('Aanoo_', '')
            if year and str(year) != y:
                continue
            items = []
            files = []
            for pat in ('*.xls', '*.xlsx', '*.csv'):
                files.extend(sorted(d.glob(pat)))
            for f in files:
                try:
                    rel = f.relative_to(root).as_posix()
                except Exception:
                    try:
                        rel = f.relative_to(base.parent).as_posix()
                    except Exception:
                        rel = f.name
                items.append({'name': f.name, 'rel': rel})
            out.append({'year': y, 'path': d.relative_to(root).as_posix(), 'files': items})
        return Response({'files': out})
    except Exception as e:
        return Response({'error': str(e), 'files': []})


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def presupuesto_completo(request):
    """GET: Lista presupuesto con datos históricos y comparaciones
    POST/PUT: Guardar/actualizar datos de presupuesto
    Usa directamente la tabla finanzas.presupuesto que contiene:
    - presupuesto: monto presupuestado
    - monto_historico: datos históricos reales
    - monto_proyectado: monto proyectado (columna generada)
    - variacion: diferencia calculada
    - variacion_porcentaje: porcentaje de variación
    - denominacion: nombre de la cuenta
    Filtros: ?year=&month=&limit=
    """
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    limit = int(request.query_params.get('limit') or '1000')
    
    where = []
    params = {}
    
    if year:
        where.append('p.anio = %(year)s::int')
        params['year'] = year
    if month:
        where.append('p.mes = %(month)s::int')
        params['month'] = month
    
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    
    # Cuando se pide por year+month, construir comparativo mensual con D anual si falta mensual
    if year and month:
        sql = f"""
            WITH p_year AS (
                SELECT 
                    p.cuenta::text AS cuenta,
                    COALESCE(
                        MAX(p.monto_proyectado) FILTER (WHERE p.monto_proyectado IS NOT NULL),
                        MAX(p.presupuesto), 0
                    )::numeric AS proyectado_anual,
                    COALESCE(MAX(p.denominacion), MAX(d.nombre_cuenta), MAX(pc.nombre), '')::text AS nombre_cuenta
                FROM finanzas.presupuesto p
                LEFT JOIN dim_cuenta d ON d.cuenta = p.cuenta
                LEFT JOIN plan_cuentas pc ON pc.cuenta = p.cuenta
                WHERE p.anio = %(year)s::int
                GROUP BY p.cuenta
            ),
            p_mes AS (
                SELECT 
                    p.cuenta::text AS cuenta,
                    COALESCE(p.monto_historico, 0)::numeric AS historico,
                    COALESCE(p.monto_proyectado, p.presupuesto, NULL)::numeric AS proyectado_mensual
                FROM finanzas.presupuesto p
                WHERE p.anio = %(year)s::int AND p.mes = %(month)s::int
            )
            SELECT 
                COALESCE(pm.cuenta, py.cuenta) AS cuenta,
                py.nombre_cuenta,
                COALESCE(pm.proyectado_mensual, py.proyectado_anual, 0)::numeric AS proyectado,
                COALESCE(pm.historico, 0)::numeric AS historico,
                (COALESCE(pm.proyectado_mensual, py.proyectado_anual, 0) - COALESCE(pm.historico, 0))::numeric AS diferencia,
                CASE 
                    WHEN COALESCE(pm.proyectado_mensual, py.proyectado_anual, 0) = 0 THEN 0
                    ELSE ROUND(((COALESCE(pm.proyectado_mensual, py.proyectado_anual, 0) - COALESCE(pm.historico, 0)) 
                                / COALESCE(pm.proyectado_mensual, py.proyectado_anual, 0)) * 100, 2)
                END::numeric AS porcentaje,
                %(year)s::text AS anio,
                %(month)s::text AS mes,
                NULL::text AS escenario,
                NULL::text AS created_at
            FROM p_year py
            LEFT JOIN p_mes pm ON pm.cuenta = py.cuenta
            ORDER BY NULLIF(COALESCE(pm.cuenta, py.cuenta), '')::numeric NULLS LAST, COALESCE(pm.cuenta, py.cuenta)
            LIMIT {limit}
        """
        params = {'year': year, 'month': month}
    else:
        sql = f"""
            SELECT 
                p.cuenta::text AS cuenta,
                COALESCE(p.denominacion, d.nombre_cuenta, pc.nombre, '')::text AS nombre_cuenta,
                p.mes::text AS mes,
                p.anio::text AS anio,
                COALESCE(p.presupuesto, 0)::numeric AS presupuesto,
                COALESCE(p.monto_historico, 0)::numeric AS historico,
                COALESCE(p.monto_proyectado, p.presupuesto, 0)::numeric AS proyectado,
                COALESCE(p.variacion, (COALESCE(p.monto_historico, 0) - COALESCE(p.presupuesto, 0)))::numeric AS diferencia,
                COALESCE(p.variacion_porcentaje, 
                    CASE 
                        WHEN COALESCE(p.presupuesto, 0) = 0 THEN 0
                        ELSE ROUND(((COALESCE(p.monto_historico, 0) - COALESCE(p.presupuesto, 0)) / COALESCE(p.presupuesto, 0)) * 100, 2)
                    END
                )::numeric AS porcentaje,
                p.escenario::text AS escenario,
                p.created_at::text AS created_at
            FROM finanzas.presupuesto p
            LEFT JOIN dim_cuenta d ON d.cuenta = p.cuenta
            LEFT JOIN plan_cuentas pc ON pc.cuenta = p.cuenta
            {where_sql}
            ORDER BY p.anio DESC, p.mes DESC, p.cuenta
            LIMIT {limit}
        """
        params = {'year': year, 'month': month}
    
    if request.method == 'GET':
        try:
            with connections['default'].cursor() as c:
                # Evitar error "dict is not a sequence" cuando no hay placeholders
                _exec(c, sql, params)
                cols = [col[0] for col in c.description]
                items = [dict(zip(cols, row)) for row in c.fetchall()]
            
            return Response({
                'source': 'finanzas.presupuesto',
                'count': len(items), 
                'items': items, 
                'filters': {'year': year, 'month': month}
            })
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"[presupuesto_completo] ERROR GET: {str(e)}")
            return Response({'error': str(e)}, status=500)
    
    elif request.method in ['POST', 'PUT']:
        # POST/PUT: Guardar/actualizar datos de presupuesto
        try:
            data = request.data
            logger = logging.getLogger(__name__)
            
            # Validar datos requeridos
            required_fields = ['cuenta', 'anio', 'mes', 'presupuesto']
            for field in required_fields:
                if field not in data:
                    return Response({'error': f'Campo requerido: {field}'}, status=400)
            
            cuenta = data['cuenta']
            anio = int(data['anio'])
            mes = int(data['mes'])
            presupuesto = float(data['presupuesto'])
            
            # Campos opcionales
            denominacion = data.get('denominacion', '')
            monto_historico = float(data.get('monto_historico', 0)) if data.get('monto_historico') else None
            monto_proyectado = float(data.get('monto_proyectado', 0)) if data.get('monto_proyectado') else None
            escenario = data.get('escenario', '')
            d_val = monto_proyectado if monto_proyectado is not None else presupuesto
            variacion = (d_val - monto_historico) if (monto_historico is not None and d_val is not None) else None
            variacion_porcentaje = ((variacion / d_val) * 100) if (variacion is not None and d_val) else None
            
            with connections['default'].cursor() as cursor:
                # Verificar si el registro ya existe
                cursor.execute("""
                    SELECT id FROM finanzas.presupuesto 
                    WHERE cuenta = %s AND anio = %s AND mes = %s
                """, [cuenta, anio, mes])
                
                existing = cursor.fetchone()
                
                if existing:
                    # Actualizar registro existente
                    cursor.execute("""
                        UPDATE finanzas.presupuesto 
                        SET presupuesto = %s, denominacion = %s, monto_historico = %s,
                            monto_proyectado = COALESCE(%s, monto_proyectado),
                            escenario = %s, variacion = %s, variacion_porcentaje = %s
                        WHERE cuenta = %s AND anio = %s AND mes = %s
                    """, [presupuesto, denominacion, monto_historico,
                          monto_proyectado, escenario, variacion, variacion_porcentaje,
                          cuenta, anio, mes])
                    message = "Registro actualizado correctamente"
                    logger.info(f"[presupuesto_completo] Actualizado: {cuenta} {anio}-{mes} = {presupuesto}")
                else:
                    # Crear nuevo registro
                    cursor.execute("""
                        INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, denominacion,
                                                          monto_historico, monto_proyectado, escenario,
                                                          variacion, variacion_porcentaje)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [cuenta, anio, mes, presupuesto, denominacion,
                          monto_historico, monto_proyectado, escenario,
                          variacion, variacion_porcentaje])
                    message = "Registro creado correctamente"
                    logger.info(f"[presupuesto_completo] Creado: {cuenta} {anio}-{mes} = {presupuesto}")
            
            return Response({'message': message}, status=200)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"[presupuesto_completo] ERROR POST/PUT: {str(e)}")
            return Response({'error': str(e)}, status=500)


# ====== Oficinas (finanzas.oficinas) - Nueva vista para snapshot mensual ======

class OficinasSnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year') or request.query_params.get('anio')
        month = request.query_params.get('month') or request.query_params.get('mes')
        q = request.query_params.get('q') or request.query_params.get('search')
        limit = int(request.query_params.get('limit') or '500')

        where = []
        params = {}
        if year:
            where.append('anio = %(anio)s::int')
            params['anio'] = year
        if month:
            where.append('mes = %(mes)s::int')
            params['mes'] = month
        if q:
            where.append('(lower(oficina_id) LIKE lower(%(q)s) OR lower(nombre_oficina) LIKE lower(%(q)s))')
            params['q'] = f"%{q}%"
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

        sql = f"""
            SELECT 
                id::bigint AS id,
                oficina_id::text AS oficina_id,
                nombre_oficina::text AS nombre_oficina,
                anio::int AS anio,
                mes::int AS mes,
                fecha_snapshot::date AS fecha_snapshot,
                entidades_financieras::int AS entidades_financieras,
                poblacion::int AS poblacion,
                created_at::text AS created_at,
                updated_at::text AS updated_at
            FROM finanzas.oficinas
            {where_sql}
            ORDER BY oficina_id, anio DESC, mes DESC
            LIMIT {limit}
        """
        try:
            with connections['default'].cursor() as c:
                _exec(c, sql, params)
                cols = [col[0] for col in c.description]
                items = [dict(zip(cols, row)) for row in c.fetchall()]
            return Response({'source': 'finanzas.oficinas', 'count': len(items), 'items': items, 'filters': {'year': year, 'month': month, 'q': q}})
        except Exception as e:
            return Response({'error': str(e), 'source': 'finanzas.oficinas'}, status=400)

    def post(self, request):
        data = request.data
        rec_id = data.get('id')
        oficina_id = (data.get('oficina_id') or '').strip()
        nombre_oficina = (data.get('nombre_oficina') or '').strip()
        
        try:
            anio = int(data.get('anio') or data.get('year'))
            mes = int(data.get('mes') or data.get('month'))
        except Exception:
            return Response({'error': 'anio y mes son requeridos y deben ser enteros'}, status=400)

        def to_int(x):
            try:
                return None if x in (None, '', '-') else int(str(x).replace(',', ''))
            except Exception:
                return None

        entidades_financieras = to_int(data.get('entidades_financieras'))
        poblacion = to_int(data.get('poblacion'))
        fecha_snapshot = data.get('fecha_snapshot') or data.get('fecha')

        if not (oficina_id and anio and mes):
            return Response({'error': 'oficina_id, anio y mes son obligatorios'}, status=400)

        with connections['default'].cursor() as c:
            if rec_id:
                # UPDATE
                c.execute(
                    """
                    UPDATE finanzas.oficinas
                    SET entidades_financieras = %s, poblacion = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    [entidades_financieras, poblacion, rec_id]
                )
                return Response({'success': True, 'updated_id': rec_id})
            else:
                # INSERT
                c.execute(
                    """
                    INSERT INTO finanzas.oficinas
                        (oficina_id, nombre_oficina, anio, mes, fecha_snapshot, entidades_financieras, poblacion)
                    VALUES (%s, %s, %s, %s, %s::date, %s, %s)
                    RETURNING id
                    """,
                    [oficina_id, nombre_oficina, anio, mes, fecha_snapshot, entidades_financieras, poblacion]
                )
                new_id = c.fetchone()[0]
                return Response({'success': True, 'id': new_id}, status=201)

    def delete(self, request):
        rec_id = request.query_params.get('id')
        if not rec_id:
            return Response({'error': 'ID es requerido para eliminar'}, status=400)
        
        try:
            with connections['default'].cursor() as c:
                c.execute(
                    "DELETE FROM finanzas.oficinas WHERE id = %s",
                    [rec_id]
                )
                if c.rowcount == 0:
                    return Response({'error': 'Registro no encontrado'}, status=404)
                return Response({'success': True, 'deleted_id': rec_id})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ====== Presupuesto APP (tabla dedicada para importaciones) ======

def _ensure_presupuesto_app_table():
    with connections['default'].cursor() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS finanzas.presupuesto_app (
              id BIGSERIAL PRIMARY KEY,
              cuenta TEXT NOT NULL,
              denominacion TEXT,
              anio INT NOT NULL,
              mes INT NOT NULL,
              proyectado NUMERIC,
              historico NUMERIC,
              created_at TIMESTAMPTZ DEFAULT NOW(),
              CONSTRAINT uq_presupuesto_app UNIQUE (cuenta, anio, mes)
            );
            """
        )


"""
-------------------------------------
 Presupuesto APP (CRUD / listado)
-------------------------------------
"""
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def presupuesto_app(request):
    _ensure_presupuesto_app_table()
    if request.method == 'GET':
        year = request.query_params.get('year') or request.query_params.get('anio')
        month = request.query_params.get('month') or request.query_params.get('mes')
        limit = int(request.query_params.get('limit') or '2000')
        where = []
        params = {}
        if year:
            where.append('anio = %(anio)s::int')
            params['anio'] = year
        if month:
            where.append('mes = %(mes)s::int')
            params['mes'] = month
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
        sql = f"""
            SELECT cuenta::text AS cuenta,
                   COALESCE(denominacion,'')::text AS nombre_cuenta,
                   anio::int AS anio,
                   mes::int AS mes,
                   COALESCE(proyectado,0)::numeric AS proyectado,
                   COALESCE(historico,0)::numeric AS historico
            FROM finanzas.presupuesto_app
            {where_sql}
            ORDER BY NULLIF(cuenta,'')::numeric NULLS LAST, cuenta
            LIMIT {limit}
        """
        with connections['default'].cursor() as c:
            _exec(c, sql, params)
            cols = [col[0] for col in c.description]
            rows = [dict(zip(cols, row)) for row in c.fetchall()]
        # añadir campos de comparativa
        items = []
        for r in rows:
            try:
                d = float(r.get('proyectado') or 0)
                e = float(r.get('historico') or 0)
            except Exception:
                d, e = 0.0, 0.0
            diff = d - e
            pct = 0.0 if d == 0 else round((diff / d) * 100, 2)
            items.append({
                'cuenta': r['cuenta'],
                'nombre_cuenta': r['nombre_cuenta'],
                'anio': r['anio'],
                'mes': r['mes'],
                'proyectado': d,
                'historico': e,
                'diferencia': diff,
                'porcentaje': pct,
            })
        return Response({'items': items, 'count': len(items), 'filters': {'year': year, 'month': month}})

    if request.method in ('POST', 'PUT'):
        data = request.data
        try:
            cuenta = str(data.get('cuenta') or data.get('codigo'))
            anio = int(data.get('anio'))
            mes = int(data.get('mes'))
        except Exception:
            return Response({'error': 'cuenta, anio, mes requeridos'}, status=400)
        denominacion = (data.get('denominacion') or '').strip()
        # aceptar solo proyectado e historico
        def to_num(x):
            try:
                return None if x in (None, '', '-') else float(x)
            except Exception:
                return None
        proyectado = to_num(data.get('proyectado'))
        historico = to_num(data.get('historico'))
        if proyectado is None:
            proyectado = 0.0
        if historico is None:
            historico = 0.0

        with connections['default'].cursor() as c:
            c.execute(
                """
                UPDATE finanzas.presupuesto_app
                   SET denominacion = COALESCE(%s, denominacion),
                       proyectado = COALESCE(%s, proyectado),
                       historico = COALESCE(%s, historico)
                 WHERE cuenta = %s AND anio = %s AND mes = %s
                """,
                [denominacion, proyectado, historico, cuenta, anio, mes]
            )
            if c.rowcount == 0:
                c.execute(
                    """
                    INSERT INTO finanzas.presupuesto_app (cuenta, denominacion, anio, mes, proyectado, historico)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [cuenta, denominacion or '', anio, mes, proyectado, historico]
                )
        return Response({'success': True, 'saved': {'cuenta': cuenta, 'anio': anio, 'mes': mes}})

    if request.method == 'DELETE':
        cuenta = request.query_params.get('cuenta') or request.query_params.get('codigo')
        year = request.query_params.get('year') or request.query_params.get('anio')
        month = request.query_params.get('month') or request.query_params.get('mes')
        if not (cuenta and year and month):
            return Response({'error': 'Se requiere cuenta, year/anio y month/mes'}, status=400)
        try:
            anio = int(year); mes = int(month)
        except Exception:
            return Response({'error': 'Año y mes deben ser enteros'}, status=400)
        with connections['default'].cursor() as c:
            c.execute("""
                DELETE FROM finanzas.presupuesto_app
                 WHERE cuenta = %s AND anio = %s AND mes = %s
            """, [cuenta, anio, mes])
            if c.rowcount == 0:
                return Response({'error': 'Registro no encontrado'}, status=404)
        return Response({'success': True, 'deleted': {'cuenta': cuenta, 'anio': anio, 'mes': mes}})
