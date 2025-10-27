"""
Coofisam360 - Vistas de Consultas SQL

Vistas para la ejecución y gestión de consultas SQL en el sistema Coofisam360.
Permite a los usuarios autorizados ejecutar consultas directas a la base de datos.

Autor: Equipo de Desarrollo Coofisam360
Versión: 1.0
"""

from django.shortcuts import render
from django.db import connections
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required
def consultas_sql(request):
    """
    Vista para ejecutar consultas SQL personalizadas.
    
    Permite a usuarios autenticados ejecutar consultas SQL directamente
    contra la base de datos principal del sistema.
    
    Args:
        request: Objeto HttpRequest con los datos del formulario
        
    Returns:
        HttpResponse: Renderiza la plantilla con los resultados o errores
    """
    result = None
    error = None

    # Procesar consulta SQL si se envía el formulario
    if request.method == 'POST':
        sql_query = request.POST.get('sql_query')
        
        if sql_query and sql_query.strip():
            try:
                # Ejecutar consulta en la base de datos principal
                with connections['default'].cursor() as cursor:
                    cursor.execute(sql_query)
                    result = cursor.fetchall()
            except Exception as e:
                error = f"Error en la consulta: {str(e)}"

    return render(request, 'consultasSQL/consultas.html', {
        'result': result, 
        'error': error
    })

@login_required
def ver_tablas(request):
    """
    Vista para mostrar todas las tablas disponibles en la base de datos.
    
    Consulta el esquema de información de PostgreSQL para obtener
    la lista de todas las tablas en el esquema público.
    
    Args:
        request: Objeto HttpRequest
        
    Returns:
        HttpResponse: Renderiza la plantilla con la lista de tablas
    """
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
        error = f"Error al consultar las tablas: {str(e)}"

    return render(request, 'consultasSQL/verTablas.html', {
        'tables': tables, 
        'error': error
    })

@login_required
def ver_vistas(request):
    """
    Vista para mostrar todas las vistas disponibles en la base de datos.
    
    Consulta el esquema de información de PostgreSQL para obtener
    la lista de todas las vistas en el esquema público.
    
    Args:
        request: Objeto HttpRequest
        
    Returns:
        HttpResponse: Renderiza la plantilla con la lista de vistas
    """
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
        error = f"Error al consultar las vistas: {str(e)}"

    return render(request, 'consultasSQL/verVistas.html', {
        'views': views, 
        'error': error
    })


@login_required
def ver_resumen_tabla(request, table_name):
    """
    Vista para mostrar la estructura de una tabla específica.
    
    Muestra los campos, tipos de datos y metadatos de una tabla
    seleccionada de la base de datos.
    
    Args:
        request: Objeto HttpRequest
        table_name (str): Nombre de la tabla a consultar
        
    Returns:
        HttpResponse: Renderiza la plantilla con la estructura de la tabla
    """
    result = None
    error = None

    try:
        # Consultar la estructura de la tabla seleccionada
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, [table_name])
            result = cursor.fetchall()
    except Exception as e:
        error = f"Error al consultar la estructura de la tabla: {str(e)}"

    return render(request, 'consultasSQL/resumenTabla.html', {
        'result': result, 
        'table_name': table_name, 
        'error': error
    })

@login_required
def ver_resumen_vista(request, view_name):
    """
    Vista para mostrar la estructura y definición de una vista específica.
    
    Muestra los campos, tipos de datos y la definición SQL de una vista
    seleccionada de la base de datos.
    
    Args:
        request: Objeto HttpRequest
        view_name (str): Nombre de la vista a consultar
        
    Returns:
        HttpResponse: Renderiza la plantilla con la estructura de la vista
    """
    result = None
    definition = None
    error = None

    try:
        with connections['default'].cursor() as cursor:
            # Consultar la estructura de la vista seleccionada
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, [view_name])
            result = cursor.fetchall()

            # Consultar la definición SQL de la vista
            cursor.execute("""
                SELECT definition 
                FROM pg_views 
                WHERE viewname = %s;
            """, [view_name])
            definition = cursor.fetchone()
            
    except Exception as e:
        error = f"Error al consultar la estructura de la vista: {str(e)}"

    return render(request, 'consultasSQL/resumenVista.html', {
        'result': result, 
        'definition': definition, 
        'view_name': view_name, 
        'error': error
    })
