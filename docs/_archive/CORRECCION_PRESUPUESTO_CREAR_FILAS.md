# Corrección: Crear Filas en Presupuesto

## Problema Identificado
El formulario de presupuesto tenía dos problemas principales:

1. **Error 405**: "Request failed with status code 405" al intentar crear nuevas filas
2. **Ordenamiento prematuro**: Las filas se ordenaban por código mientras se estaban editando, moviendo la fila que se estaba creando

## Causas del Problema

### 1. Error 405 - Método No Permitido
- **Causa**: El backend `PresupuestoView` solo tenía método `GET`, no tenía `POST`
- **Síntoma**: Error 405 al intentar guardar nuevas filas
- **Ubicación**: `/home/desarrollo/coofisam360/backend/django/users/api_views.py`

### 2. Ordenamiento Prematuro
- **Causa**: Las filas se ordenaban por código en cada cambio, incluso las filas nuevas
- **Síntoma**: La fila que se está creando se mueve de posición mientras se edita
- **Ubicación**: `/home/desarrollo/Coofisam360-Frontend/app/modulo-financiero/tabla-presupuesto/page.js`

### 3. URL Incorrecta en Servicio
- **Causa**: El servicio usaba URL relativa en lugar de absoluta
- **Síntoma**: Posibles errores de conexión
- **Ubicación**: `/home/desarrollo/Coofisam360-Frontend/app/services/modulo-financiero/presupuesto.js`

## Soluciones Implementadas

### 1. Agregado Método POST al Backend
**Archivo**: `/home/desarrollo/coofisam360/backend/django/users/api_views.py`

```python
def post(self, request):
    """Crear o actualizar un registro de presupuesto"""
    try:
        data = request.data
        cuenta = data.get('cuenta')
        nombre_cuenta = data.get('nombre_cuenta', '')
        anio = data.get('anio')
        mes = data.get('mes')
        presupuesto = data.get('presupuesto', 0)

        # Validar campos requeridos
        if not cuenta or not anio or not mes:
            return Response({'error': 'Cuenta, año y mes son campos requeridos'}, status=400)

        # Convertir a tipos correctos
        try:
            anio = int(anio)
            mes = int(mes)
            presupuesto = float(presupuesto) if presupuesto else 0.0
        except (ValueError, TypeError):
            return Response({'error': 'Año, mes y presupuesto deben ser números válidos'}, status=400)

        with connections['default'].cursor() as c:
            # Intentar actualizar primero
            c.execute("""
                UPDATE finanzas.presupuesto 
                SET presupuesto = %s, updated_at = CURRENT_TIMESTAMP
                WHERE cuenta = %s AND anio = %s AND mes = %s
            """, [presupuesto, cuenta, anio, mes])
            
            # Si no se actualizó ninguna fila, insertar nueva
            if c.rowcount == 0:
                c.execute("""
                    INSERT INTO finanzas.presupuesto (cuenta, anio, mes, presupuesto, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [cuenta, anio, mes, presupuesto])

        return Response({'message': 'Registro guardado correctamente'}, status=200)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"[PresupuestoView POST] Error: {str(e)}")
        return Response({'error': str(e)}, status=500)
```

### 2. Corregido Ordenamiento en Frontend
**Archivo**: `/home/desarrollo/Coofisam360-Frontend/app/modulo-financiero/tabla-presupuesto/page.js`

#### A. Modificado `loadData()`:
```javascript
// Separar filas nuevas de las existentes
const newRows = rows.filter(r => r.isNew);
const existingRows = [...transformedData];

// Ordenar solo las filas existentes por código
const sortedExisting = existingRows.sort((a, b) => {
  const codeA = parseInt(a.codigo) || 0;
  const codeB = parseInt(b.codigo) || 0;
  return codeA - codeB;
});

// Mantener filas nuevas al principio
const finalRows = [...newRows, ...sortedExisting];
```

#### B. Modificado `useEffect` de búsqueda:
```javascript
.sort((a, b) => {
  // Mantener filas nuevas al principio
  if (a.isNew && !b.isNew) return -1;
  if (!a.isNew && b.isNew) return 1;
  
  // Ordenar por código solo si no son filas nuevas
  if (!a.isNew && !b.isNew) {
    const codeA = parseInt(a.codigo) || 0;
    const codeB = parseInt(b.codigo) || 0;
    return codeA - codeB;
  }
  
  return 0;
});
```

### 3. Corregidas URLs en Servicio
**Archivo**: `/home/desarrollo/Coofisam360-Frontend/app/services/modulo-financiero/presupuesto.js`

```javascript
// Función para guardar registro de presupuesto
export async function savePresupuesto(data) {
  try {
    const response = await api.post(`${API_BASE_URL}/api/v1/finanzas/presupuesto/`, data);
    return response.data;
  } catch (error) {
    console.error("Error al guardar presupuesto:", error);
    throw error;
  }
}

// Función para eliminar registro de presupuesto
export async function deletePresupuesto(id) {
  try {
    const response = await api.delete(`${API_BASE_URL}/api/v1/finanzas/presupuesto/${id}/`);
    return response.data;
  } catch (error) {
    console.error("Error al eliminar presupuesto:", error);
    throw error;
  }
}
```

## Comportamiento Corregido

### Antes:
1. ❌ Error 405 al intentar crear filas
2. ❌ Las filas se movían mientras se editaban
3. ❌ Ordenamiento prematuro por código

### Después:
1. ✅ Las filas nuevas se crean correctamente
2. ✅ Las filas nuevas permanecen al principio mientras se editan
3. ✅ El ordenamiento por código solo ocurre después de guardar
4. ✅ Las filas guardadas se ordenan correctamente por código

## Flujo de Trabajo Mejorado

1. **Crear Fila**: 
   - Se agrega al principio de la tabla
   - Se marca como `isNew: true`
   - No se ordena por código

2. **Editar Fila Nueva**:
   - Permanece en su posición
   - No se mueve durante la edición
   - Mantiene el indicador "NUEVO"

3. **Guardar Fila**:
   - Se envía al backend via POST
   - Se marca como `isNew: false`
   - Se reordena por código en la próxima carga

4. **Recargar Datos**:
   - Las filas guardadas se ordenan por código
   - Las filas nuevas permanecen al principio

## Validaciones Implementadas

### Backend:
- ✅ Cuenta, año y mes son campos requeridos
- ✅ Validación de tipos numéricos
- ✅ Validación de clave foránea (cuenta debe existir en plan_cuentas)
- ✅ Manejo de errores con logging

### Frontend:
- ✅ Validación de campos requeridos antes de guardar
- ✅ Preservación de filas nuevas durante edición
- ✅ Ordenamiento inteligente (nuevas primero, luego por código)

## Consideraciones Importantes

### Restricción de Clave Foránea
La tabla `finanzas.presupuesto` tiene una restricción de clave foránea que requiere que la `cuenta` exista en la tabla `plan_cuentas`. Esto significa que:

- ✅ Solo se pueden crear registros con cuentas que ya existen en el plan de cuentas
- ❌ No se pueden crear registros con cuentas nuevas sin antes agregarlas al plan de cuentas
- ✅ El sistema valida automáticamente esta restricción en el backend

### Pruebas Realizadas
- ✅ Endpoint POST funciona correctamente
- ✅ Validación de campos requeridos
- ✅ Validación de tipos numéricos
- ✅ Validación de clave foránea
- ✅ Inserción y actualización de registros

## Resultado Final
El formulario de presupuesto ahora permite:
- ✅ Crear nuevas filas sin errores
- ✅ Editar filas sin que se muevan de posición
- ✅ Guardar correctamente en la base de datos
- ✅ Ordenar por código solo después de guardar
- ✅ Mantener una experiencia de usuario fluida
- ✅ Validar restricciones de base de datos
