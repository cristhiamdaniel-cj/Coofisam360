# Corrección: Eliminar Registros en Presupuesto

## Problema Identificado
El formulario de presupuesto mostraba error **404** al intentar eliminar registros existentes.

### Síntoma:
- Error: "Request failed with status code 404"
- No se podían eliminar registros de la base de datos
- Solo se podían eliminar filas nuevas (que no estaban guardadas)

## Causa del Problema

### 1. Endpoint DELETE Faltante
- **Causa**: La clase `PresupuestoView` en el backend solo tenía métodos `GET` y `POST`
- **Síntoma**: Error 404 al intentar hacer DELETE
- **Ubicación**: `/home/desarrollo/coofisam360/backend/django/users/api_views.py`

### 2. URL con Parámetro Faltante
- **Causa**: No estaba configurada la URL para manejar DELETE con ID
- **Síntoma**: Django no podía enrutar la petición DELETE
- **Ubicación**: `/home/desarrollo/coofisam360/backend/django/users/api_urls.py`

## Soluciones Implementadas

### 1. Agregado Método DELETE al Backend
**Archivo**: `/home/desarrollo/coofisam360/backend/django/users/api_views.py`

```python
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
```

### 2. Agregada URL con Parámetro
**Archivo**: `/home/desarrollo/coofisam360/backend/django/users/api_urls.py`

```python
# URL existente para GET y POST
path('finanzas/presupuesto/', api_views.PresupuestoView.as_view(), name='api-finanzas-presupuesto-list'),

# Nueva URL para DELETE con parámetro ID
path('finanzas/presupuesto/<str:id>/', api_views.PresupuestoView.as_view(), name='api-finanzas-presupuesto-detail'),
```

## Funcionalidad Implementada

### Formato de ID
El sistema usa un formato específico para identificar registros:
- **Formato**: `cuenta_anio_mes`
- **Ejemplo**: `4_2025_1` (cuenta 4, año 2025, mes 1)

### Validaciones Implementadas
1. **ID Requerido**: Verifica que se proporcione un ID
2. **Formato Válido**: Valida que el ID tenga el formato correcto
3. **Registro Existe**: Verifica que el registro exista antes de eliminar
4. **Tipos Correctos**: Convierte año y mes a enteros

### Manejo de Errores
- **400**: ID requerido o formato inválido
- **404**: Registro no encontrado
- **500**: Error interno del servidor

## Pruebas Realizadas

### 1. Prueba de Eliminación Exitosa
```bash
curl -X DELETE "http://localhost:8060/api/v1/finanzas/presupuesto/4_2025_1/" \
  -H "Authorization: Token ff6c34cf9e07b35bd5a26f65cdb356ed00ce7c47"
```
**Resultado**: `{"message":"Registro eliminado correctamente"}`

### 2. Verificación de Eliminación
```bash
curl -X GET "http://localhost:8060/api/v1/finanzas/presupuesto/?year=2025&month=1" \
  -H "Authorization: Token ff6c34cf9e07b35bd5a26f65cdb356ed00ce7c47"
```
**Resultado**: El registro ya no aparece en la respuesta

### 3. Prueba de Registro No Encontrado
```bash
curl -X DELETE "http://localhost:8060/api/v1/finanzas/presupuesto/999_2025_1/" \
  -H "Authorization: Token ff6c34cf9e07b35bd5a26f65cdb356ed00ce7c47"
```
**Resultado**: `{"error":"Registro no encontrado"}` (404)

## Comportamiento Corregido

### Antes:
- ❌ Error 404 al intentar eliminar
- ❌ Solo se podían eliminar filas nuevas
- ❌ No se podían eliminar registros de la base de datos

### Después:
- ✅ Eliminación exitosa de registros existentes
- ✅ Confirmación doble en el frontend
- ✅ Eliminación tanto de filas nuevas como existentes
- ✅ Mensajes de confirmación apropiados
- ✅ Manejo robusto de errores

## Flujo de Eliminación

1. **Usuario hace clic en "Eliminar"**:
   - Se muestra primera confirmación
   - Se muestra segunda confirmación

2. **Si es fila nueva**:
   - Se elimina del estado local
   - No se hace petición al backend

3. **Si es fila existente**:
   - Se hace petición DELETE al backend
   - Se elimina de la base de datos
   - Se actualiza el estado local

4. **Resultado**:
   - Fila eliminada de la tabla
   - Mensaje de confirmación mostrado
   - Estado actualizado correctamente

## Integración con Frontend

El frontend ya tenía la lógica correcta implementada:
- ✅ Confirmación doble
- ✅ Manejo de filas nuevas vs existentes
- ✅ Actualización del estado local
- ✅ Mensajes de estado
- ✅ Manejo de errores

Solo faltaba la implementación del backend, que ahora está completa.

## Resultado Final
El formulario de presupuesto ahora permite:
- ✅ Eliminar registros existentes de la base de datos
- ✅ Eliminar filas nuevas del estado local
- ✅ Confirmación doble para evitar eliminaciones accidentales
- ✅ Mensajes de confirmación apropiados
- ✅ Manejo robusto de errores
- ✅ Experiencia de usuario consistente


