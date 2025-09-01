# consultasSQL/views.py
from django.shortcuts import render
from django.db import connections
from django.http import HttpResponse

def consultas_sql(request):
    """Vista para recibir y ejecutar consultas SQL"""
    result = None
    error = None

    # Si el formulario es enviado, procesamos la consulta
    if request.method == 'POST':
        sql_query = request.POST.get('sql_query')  # Obtener la consulta desde el formulario

        if sql_query:
            try:
                # Usamos la base de datos 'default' (coofisam_db) para ejecutar la consulta
                with connections['default'].cursor() as cursor:
                    cursor.execute(sql_query)
                    result = cursor.fetchall()  # Obtener todos los resultados de la consulta
            except Exception as e:
                error = str(e)  # Si hay un error, mostrarlo

    return render(request, 'consultasSQL/consultas.html', {'result': result, 'error': error})

def ver_tablas(request):
    """Vista para ver las tablas en la base de datos"""
    tables = None
    error = None

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
    except Exception as e:
        error = str(e)

    return render(request, 'consultasSQL/verTablas.html', {'tables': tables, 'error': error})

def ver_vistas(request):
    """Vista para ver las vistas en la base de datos"""
    views = None
    error = None

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema='public'
                ORDER BY table_name;
            """)
            views = cursor.fetchall()
    except Exception as e:
        error = str(e)

    return render(request, 'consultasSQL/verVistas.html', {'views': views, 'error': error})


def ver_resumen_tabla(request, table_name):
    """Vista para ver los campos y tipos de datos de una tabla seleccionada"""
    result = None
    error = None

    try:
        # Consultar los campos de la tabla seleccionada
        with connections['default'].cursor() as cursor:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table_name}';")
            result = cursor.fetchall()
    except Exception as e:
        error = str(e)

    return render(request, 'consultasSQL/resumenTabla.html', {'result': result, 'table_name': table_name, 'error': error})

def ver_resumen_vista(request, view_name):
    """Vista para ver los campos y la definición SQL de una vista seleccionada"""
    result = None
    definition = None
    error = None

    try:
        # Consultar los campos de la vista seleccionada
        with connections['default'].cursor() as cursor:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{view_name}';")
            result = cursor.fetchall()

        # Consultar la definición SQL de la vista
        cursor.execute(f"SELECT definition FROM pg_views WHERE viewname='{view_name}';")
        definition = cursor.fetchone()
    except Exception as e:
        error = str(e)

    return render(request, 'consultasSQL/resumenVista.html', {'result': result, 'definition': definition, 'view_name': view_name, 'error': error})
