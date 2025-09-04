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
BALANCE_ROOT = "/home/desarrollo/Coofisam/data/Libro_de_Balance_x_Aanoo"

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


# ====== ETL: streaming de logs por SSE (opcional ya listo) ======
@login_required
def finanzas_etl_stream(request):
    """
    GET /finanzas/etl/stream/
    Ejecuta: cd /home/desarrollo/Coofisam && source .venv/bin/activate && python cargue_balance_agencias_coreNuevo.py
    y envía stdout/stderr por Server-Sent Events.
    """
    def event_stream():
        yield "data: 🚀 Iniciando ETL...\n\n"
        cmd = (
            'bash -lc "cd /home/desarrollo/Coofisam && '
            'source .venv/bin/activate && '
            'python cargue_balance_agencias_coreNuevo.py"'
        )
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=True, bufsize=1, universal_newlines=True
        )
        for line in proc.stdout:
            yield f"data: {line.rstrip()}\n\n"
        proc.wait()
        yield f"data: 🏁 ETL finalizado (código {proc.returncode})\n\n"

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
