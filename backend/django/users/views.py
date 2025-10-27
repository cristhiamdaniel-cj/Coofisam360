# # users/views.py
# from django.contrib.auth import authenticate, login, logout
# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required
# from django.http import JsonResponse, HttpResponseForbidden
# import os
# import re
# import unicodedata
# from datetime import datetime
# from pathlib import Path

# # ====== Vistas generales ======

# def home_view(request):
#     """Vista de bienvenida después de login"""
#     return render(request, 'home.html')  # Asegúrate de tener la plantilla 'home.html'


# def login_view(request):
#     """Vista para el login"""
#     # Si el usuario ya está autenticado, redirigirlo a la página de inicio (home)
#     if request.user.is_authenticated:
#         return redirect('home')

#     if request.method == 'POST':
#         from .forms import LoginForm
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             username = form.cleaned_data['username']
#             password = form.cleaned_data['password']
#             user = authenticate(request, username=username, password=password)

#             if user is not None:
#                 login(request, user)
#                 return redirect('home')
#             else:
#                 form.add_error(None, 'Nombre de usuario o contraseña incorrectos')
#     else:
#         from .forms import LoginForm
#         form = LoginForm()

#     return render(request, 'login.html', {'form': form})


# def index_view(request):
#     """Redirige a login si el usuario no está autenticado"""
#     if request.user.is_authenticated:
#         return redirect('home')
#     else:
#         return redirect('login')


# def logout_view(request):
#     """Cerrar sesión y redirigir al login"""
#     logout(request)
#     return redirect('login')


# # ====== Vistas del Módulo Financiero ======

# @login_required
# def modulo_financiero(request):
#     return render(request, "finanzas/home.html")


# @login_required
# def finanzas_carga_balance(request):
#     return render(request, "finanzas/carga_balance.html")


# @login_required
# def finanzas_form_indicadores(request):
#     return render(request, "finanzas/form_indicadores.html")


# @login_required
# def finanzas_form_cupos(request):
#     return render(request, "finanzas/form_cupos.html")


# # ====== API: Árbol de archivos para Libro de Balance ======
# # Directorio RAÍZ donde está tu estructura real:
# # /home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo
# BALANCE_ROOT = "/home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo"


# def _build_tree(path: str) -> dict:
#     """
#     Retorna un dict con la estructura de directorios/archivos.
#     {
#       "name": str,
#       "type": "dir" | "file",
#       "children": [ ... ]  # solo si es dir
#     }
#     """
#     node = {"name": os.path.basename(path) or path, "type": "dir", "children": []}
#     try:
#         with os.scandir(path) as it:
#             # Directorios primero, luego archivos (ambos ordenados alfabéticamente)
#             for entry in sorted(it, key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower())):
#                 if entry.is_dir(follow_symlinks=False):
#                     node["children"].append(_build_tree(entry.path))
#                 else:
#                     node["children"].append({"name": entry.name, "type": "file"})
#     except PermissionError:
#         node["children"].append({"name": "[permiso denegado]", "type": "file"})
#     return node


# @login_required
# def finanzas_api_tree(request):
#     """
#     GET /finanzas/api/tree/
#     Devuelve JSON con el árbol del directorio BALANCE_ROOT.
#     """
#     if request.method != "GET":
#         return HttpResponseForbidden("Método no permitido")

#     root = BALANCE_ROOT
#     if not os.path.exists(root):
#         return JsonResponse({"error": f"Ruta no existe: {root}"}, status=404)

#     data = _build_tree(root)
#     return JsonResponse(
#         {"root": os.path.basename(root), "tree": data.get("children", [])},
#         json_dumps_params={"ensure_ascii": False}
#     )


# # ====== API: Subida de archivos ======
# # Reglas:
# # - Nombre esperado: Listado_balances_Consolidado_<Mes>_<Año>.xlsx
# # - Se guarda en: /.../Libro_de_Balance_x_Aanoo/Aanoo_<AÑO>/
# # - Si existe, versiona con timestamp para no sobrescribir

# # Normaliza texto (quita acentos y baja a minúsculas)
# def _norm(s: str) -> str:
#     return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()

# # Mapa de meses (acepta "septiembre" y "setiembre")
# MESES = {
#     'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
#     'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
#     'septiembre': 9, 'setiembre': 9,
#     'octubre': 10, 'noviembre': 11, 'diciembre': 12,
# }

# # Regex flexible para el nombre (permite guiones/barras bajas/espacios, mayúsculas/minúsculas y acentos)
# FNAME_RE = re.compile(
#     r'listado[\s_-]*balances[\s_-]*consolidado[\s_-]*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)[\s_-]*(\d{4})\.(xlsx|xls)$',
#     re.IGNORECASE
# )

# @login_required
# def upload_libro_balance(request):
#     """
#     POST /finanzas/upload/
#     Sube un Excel con nombre: Listado_balances_Consolidado_<Mes>_<Año>.xlsx
#     y lo guarda en: /.../Libro_de_Balance_x_Aanoo/Aanoo_<AÑO>/
#     Validaciones:
#       - Nombre debe cumplir patrón.
#       - Si ya existe un archivo con ese nombre → error.
#     """
#     if request.method != "POST":
#         return HttpResponseForbidden("Método no permitido")

#     f = request.FILES.get('file')
#     if not f:
#         return JsonResponse(
#             {"success": False, "error": "Archivo no encontrado (campo 'file')."},
#             status=400
#         )

#     # Validar extensión y patrón de nombre
#     m = FNAME_RE.search(f.name)
#     if not m:
#         return JsonResponse({
#             "success": False,
#             "error": "Nombre inválido. Usa: Listado_balances_Consolidado_<Mes>_<Año>.xlsx"
#         }, status=400)

#     mes_txt, anio_txt = m.group(1), m.group(2)
#     mes_key = _norm(mes_txt)
#     if mes_key not in MESES:
#         return JsonResponse(
#             {"success": False, "error": f"Mes no reconocido: {mes_txt}"},
#             status=400
#         )

#     anio = int(anio_txt)

#     # Carpeta destino: Aanoo_<AÑO>
#     base_dir = Path(BALANCE_ROOT)
#     target_dir = base_dir / f"Aanoo_{anio}"
#     target_dir.mkdir(parents=True, exist_ok=True)

#     original_name = Path(f.name).name
#     dest_path = target_dir / original_name

#     # Validar duplicado
#     if dest_path.exists():
#         return JsonResponse(
#             {"success": False, "error": f"Ya existe un archivo con ese nombre en {target_dir}"},
#             status=400
#         )

#     # Guardar archivo
#     with open(dest_path, "wb+") as dst:
#         for chunk in f.chunks():
#             dst.write(chunk)

#     return JsonResponse({
#         "success": True,
#         "saved_name": dest_path.name,
#         "anio_dir": f"Aanoo_{anio}",
#         "dest_path": str(dest_path),
#     })

# users/views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, StreamingHttpResponse
import os
import re
import unicodedata
import subprocess
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.db import connections, transaction

# ====== Vistas generales ======

def home_view(request):
    """Vista de bienvenida después de login"""
    return render(request, 'home.html')  # Asegúrate de tener la plantilla 'home.html'


def login_view(request):
    """Vista para el login"""
    if request.user.is_authenticated:
        return redirect('users:home')  # <— namespace

    if request.method == 'POST':
        from .forms import LoginForm
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('users:home')  # <— namespace
            else:
                form.add_error(None, 'Nombre de usuario o contraseña incorrectos')
    else:
        from .forms import LoginForm
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def index_view(request):
    """Redirige a login si el usuario no está autenticado"""
    if request.user.is_authenticated:
        return redirect('users:home')   # <— namespace
    else:
        return redirect('users:login')  # <— namespace


def logout_view(request):
    """Cerrar sesión y redirigir al login"""
    logout(request)
    return redirect('users:login')      # <— namespace


# ====== Vistas del Módulo Financiero ======

@login_required
def modulo_financiero(request):
    return render(request, "finanzas/home.html")


@login_required
def finanzas_carga_balance(request):
    return render(request, "finanzas/carga_balance.html")


@login_required
def finanzas_form_indicadores(request):
    return render(request, "finanzas/form_indicadores.html")


@login_required
def finanzas_form_cupos(request):
    return render(request, "finanzas/form_cupos.html")


# ====== API: Árbol de archivos para Libro de Balance ======
# Usar la ruta configurada en settings para unificar ubicación de archivos subidos
BALANCE_ROOT = str(getattr(settings, 'LIBRO_BALANCE_ROOT', "/home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo"))

def _build_tree(path: str) -> dict:
    node = {"name": os.path.basename(path) or path, "type": "dir", "children": []}
    try:
        with os.scandir(path) as it:
            for entry in sorted(it, key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower())):
                if entry.is_dir(follow_symlinks=False):
                    node["children"].append(_build_tree(entry.path))
                else:
                    node["children"].append({"name": entry.name, "type": "file"})
    except PermissionError:
        node["children"].append({"name": "[permiso denegado]", "type": "file"})
    return node


@login_required
def finanzas_api_tree(request):
    if request.method != "GET":
        return HttpResponseForbidden("Método no permitido")

    root = BALANCE_ROOT
    if not os.path.exists(root):
        return JsonResponse({"error": f"Ruta no existe: {root}"}, status=404)

    data = _build_tree(root)
    return JsonResponse(
        {"root": os.path.basename(root), "tree": data.get("children", [])},
        json_dumps_params={"ensure_ascii": False}
    )


# ====== API: Subida de archivos ======
def _norm(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()

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

@login_required
def upload_libro_balance(request):
    """
    POST /finanzas/upload/
    Valida nombre: Listado_balances_Consolidado_<Mes>_<Año>.xlsx
    Guarda en: .../Libro_de_Balance_x_Aanoo/Aanoo_<AÑO>/
    No sobrescribe: si existe → error.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    f = request.FILES.get('file')
    if not f:
        return JsonResponse({"success": False, "error": "Archivo no encontrado (campo 'file')."}, status=400)

    m = FNAME_RE.search(f.name)
    if not m:
        return JsonResponse({
            "success": False,
            "error": "Nombre inválido. Usa: Listado_balances_Consolidado_<Mes>_<Año>.xlsx"
        }, status=400)

    mes_txt, anio_txt = m.group(1), m.group(2)
    if _norm(mes_txt) not in MESES:
        return JsonResponse({"success": False, "error": f"Mes no reconocido: {mes_txt}"}, status=400)

    anio = int(anio_txt)
    target_dir = Path(BALANCE_ROOT) / f"Aanoo_{anio}"
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_path = target_dir / Path(f.name).name
    if dest_path.exists():
        return JsonResponse(
            {"success": False, "error": f"Ya existe un archivo con ese nombre en {target_dir}"},
            status=400
        )

    with open(dest_path, "wb+") as dst:
        for chunk in f.chunks():
            dst.write(chunk)

    return JsonResponse({
        "success": True,
        "saved_name": dest_path.name,
        "anio_dir": f"Aanoo_{anio}",
        "dest_path": str(dest_path),
    })


# ====== ETL: streaming de logs por SSE (con soporte de token o sesión) ======
def finanzas_etl_stream(request):
    """
    GET /finanzas/etl/stream/
    Ejecuta: cd /home/desarrollo/Coofisam && source .venv/bin/activate && python cargue_balance_agencias_coreNuevo.py
    y envía stdout/stderr por Server-Sent Events.
    """
    # Autenticación: sesión o token en query/header
    try:
        from rest_framework.authtoken.models import Token
    except Exception:
        Token = None

    user_ok = False
    if request.user.is_authenticated:
        user_ok = True
    else:
        token = request.GET.get('token') or request.headers.get('Authorization', '').replace('Token ', '').strip()
        if token and Token is not None:
            try:
                t = Token.objects.select_related('user').get(key=token)
                user_ok = t.user is not None
            except Exception:
                user_ok = False
    if not user_ok:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Auth requerida (sesión activa o token)')
    # Parámetros de post-proceso
    def _truthy(v):
        return str(v).lower() in ('1', 'true', 'yes', 'on')
    try:
        y = int(request.GET.get('year')) if request.GET.get('year') else None
        m = int(request.GET.get('month')) if request.GET.get('month') else None
    except Exception:
        y, m = None, None
    # Defaults: si no se reciben banderas, asumimos true (oculto al usuario)
    def _truthy_default_true(val):
        if val is None:
            return True
        return _truthy(val)
    pop_public = _truthy_default_true(request.GET.get('populate_public_saldos'))
    pop_op = _truthy_default_true(request.GET.get('populate_op_saldo'))

    def event_stream():
        final_m = m
        yield "data: 🚀 Iniciando ETL...\n\n"
        # Pasar parámetros al script por variables de entorno
        root_dir = getattr(settings, 'LIBRO_BALANCE_ROOT', "/home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo")
        file_rel = request.GET.get('file') or request.GET.get('file_rel') or ''
        try:
            yield f"data: ℹ Parámetros: year={y or '-'} file={file_rel or '[none]'}\n\n"
        except Exception:
            pass
        try:
            # Si no viene mes, intentar derivarlo del nombre del archivo (Consolidado_<Mes>_<Año>)
            if not final_m and file_rel:
                import re
                name = str(file_rel).split('/')[-1]
                m_map = {
                    'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
                    'julio':7,'agosto':8,'septiembre':9,'setiembre':9,
                    'octubre':10,'noviembre':11,'diciembre':12
                }
                mm = None
                try:
                    rx = re.compile(r"consolidado[_\s-]*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)", re.IGNORECASE)
                    mname = rx.search(name)
                    if mname:
                        key = (
                            ''.join(c for c in mname.group(1) if c.isalpha())
                            .lower()
                            .replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                        )
                        mm = m_map.get(key)
                except Exception:
                    mm = None
                if mm:
                    final_m = mm
            env_parts = []
            if y:
                env_parts.append(f"ETL_YEAR={y}")
            if final_m:
                env_parts.append(f"ETL_MONTH={final_m}")
            if file_rel:
                # Sanitizar comillas
                safe_file = file_rel.replace('"', '\\"')
                env_parts.append(f"ETL_FILE_REL=\"{safe_file}\"")
            if root_dir:
                safe_root = str(root_dir).replace('"', '\\"')
                env_parts.append(f"ETL_ROOT_DIR=\"{safe_root}\"")
            # Forzar salida sin buffer del script Python
            env_parts.append("PYTHONUNBUFFERED=1")
            env_export = ' '.join(env_parts)
            # Exponer mes final detectado
            try:
                yield f"data: ℹ Mes detectado: {final_m or '-'}\n\n"
            except Exception:
                pass
        except Exception as e:
            yield f"data: ❌ Error preparando entorno ETL: {str(e)}\\n\\n"
            return
        try:
            yield f"data: ℹ Entorno: {env_export or '[vacío]'}\n\n"
        except Exception:
            pass

        venv_py = '/home/desarrollo/Coofisam/.venv/bin/python'
        cmd = (
            'bash -lc "cd /home/desarrollo/Coofisam && '
            f'{env_export} {venv_py} -u cargue_balance_agencias_coreNuevo.py"'
        )
        # Log de comando resumido (sin rutas completas) para diagnóstico en cliente
        try:
            fname = (file_rel or '').split('/')[-1]
            yield f"data: ▶ Ejecutando archivo: {fname or '[sin archivo]'} | Año: {y or '-'}\\n\\n"
        except Exception:
            pass
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=True, bufsize=1, universal_newlines=True
            )
        except Exception as e:
            yield f"data: ❌ Error iniciando proceso ETL: {str(e)}\\n\\n"
            return
        yield f"data: ▶ Proceso lanzado (pid={getattr(proc, 'pid', '-')})\\n\\n"
        for line in proc.stdout:
            yield f"data: {line.rstrip()}\n\n"
        proc.wait()
        yield f"data: 🏁 ETL finalizado (código {proc.returncode})\n\n"

        # Post-procesamiento: poblar tablas si vienen parámetros válidos
        if y and final_m and 1 <= int(final_m) <= 12:
            try:
                # Conteo en staging previo (debug)
                try:
                    with connections['default'].cursor() as dbg:
                        dbg.execute(
                            "SELECT COUNT(*) FROM staging.saldos_agencia WHERE anio=%s AND mes=%s",
                            [y, final_m],
                        )
                        staging_cnt = dbg.fetchone()[0]
                    yield f"data: 📦 staging.saldos_agencia (previo) periodo={y}-{int(final_m):02d}: {staging_cnt} filas\n\n"
                except Exception as _e:
                    yield f"data: ⚠️ staging count no disponible: {_e}\n\n"
                yield f"data: 🔄 Población de tablas para {y}-{int(final_m):02d}...\n\n"
                with transaction.atomic():
                    with connections['default'].cursor() as cur:
                        if pop_public:
                            cur.execute("DELETE FROM public.saldos_agencia WHERE anio=%s AND mes=%s", [y, final_m])
                            # ¿Existe staging.saldos_agencia?
                            cur.execute("""
                              SELECT EXISTS(
                                SELECT 1 FROM information_schema.tables
                                WHERE table_schema='staging' AND table_name='saldos_agencia'
                              )
                            """)
                            has_staging = bool(cur.fetchone()[0])
                            if has_staging:
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
                                  [y, final_m]
                                )
                                ins0 = cur.rowcount or 0
                                yield f"data: ✅ public.saldos_agencia upsert (staging) filas={ins0}\n\n"
                                if ins0 == 0:
                                    # Fallback si staging no tiene filas del período
                                    cur.execute(
                                      """
                                      INSERT INTO public.saldos_agencia
                                        (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                                      SELECT '14', o.anio, o.mes, po.codigo, 0, 0, 0, COALESCE(NULLIF(o.cta_puc_14,''),'0')::numeric
                                      FROM finanzas.oficinas o
                                      JOIN public.oficinas po ON po.id=o.oficina_id
                                      WHERE o.anio=%s AND o.mes=%s
                                      ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                                      DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                                      """,
                                      [y, final_m]
                                    )
                                    ins1 = cur.rowcount or 0
                                    cur.execute(
                                      """
                                      INSERT INTO public.saldos_agencia
                                        (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                                      SELECT '21', o.anio, o.mes, po.codigo, 0, 0, 0, COALESCE(NULLIF(o.cta_puc_21,''),'0')::numeric
                                      FROM finanzas.oficinas o
                                      JOIN public.oficinas po ON po.id=o.oficina_id
                                      WHERE o.anio=%s AND o.mes=%s
                                      ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                                      DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                                      """,
                                      [y, final_m]
                                    )
                                    ins2 = cur.rowcount or 0
                                    yield f"data: 🔁 Fallback 14/21 aplicado, filas={ins1+ins2}\n\n"
                            else:
                                # Fallback: 14/21 desde finanzas.oficinas
                                cur.execute(
                                  """
                                  INSERT INTO public.saldos_agencia
                                    (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                                  SELECT '14', o.anio, o.mes, po.codigo, 0, 0, 0, COALESCE(NULLIF(o.cta_puc_14,''),'0')::numeric
                                  FROM finanzas.oficinas o
                                  JOIN public.oficinas po ON po.id=o.oficina_id
                                  WHERE o.anio=%s AND o.mes=%s
                                  ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                                  DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                                  """,
                                  [y, final_m]
                                )
                                ins1 = cur.rowcount or 0
                                cur.execute(
                                  """
                                  INSERT INTO public.saldos_agencia
                                    (cuenta, anio, mes, agencia_codigo, saldo_inicial, debito, credito, saldo_final)
                                  SELECT '21', o.anio, o.mes, po.codigo, 0, 0, 0, COALESCE(NULLIF(o.cta_puc_21,''),'0')::numeric
                                  FROM finanzas.oficinas o
                                  JOIN public.oficinas po ON po.id=o.oficina_id
                                  WHERE o.anio=%s AND o.mes=%s
                                  ON CONFLICT (cuenta, anio, mes, agencia_codigo)
                                  DO UPDATE SET saldo_final=EXCLUDED.saldo_final
                                  """,
                                  [y, final_m]
                                )
                                ins2 = cur.rowcount or 0
                                yield f"data: ✅ public.saldos_agencia upsert (fallback 14/21) filas={ins1+ins2}\n\n"
                        if pop_op:
                            cur.execute("CALL finanzas.sp_apply_saldos_mes(%s, %s);", [y, final_m])
                            yield f"data: ✅ finanzas.op_saldo_mensual consolidado para {y}-{final_m:02d}\n\n"
                yield "data: 🟢 Población completada.\n\n"
            except Exception as e:
                yield f"data: ❌ Error poblando tablas: {str(e)}\n\n"

    resp = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    return resp

from django.http import JsonResponse
from django.shortcuts import render

def home_view(request):
    """Vista principal de Coofisam360"""
    context = {
        'title': 'Coofisam360 - Sistema Integral',
        'message': 'Bienvenido a Coofisam360',
        'api_status': 'Funcionando',
        'version': '1.0'
    }
    return render(request, 'home.html', context)

def api_info(request):
    """Información de la API"""
    return JsonResponse({
        'app': 'Coofisam360',
        'status': 'active',
        'api_version': '1.0',
        'endpoints': {
            'api': '/api/v1/',
            'admin': '/admin/',
            'users': '/users/',
            'consultas': '/consultas/'
        },
        'message': 'API funcionando correctamente'
    })
