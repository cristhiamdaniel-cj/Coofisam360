# Corrección: Error 400 al Eliminar Filas Guardadas

## Problema Identificado
Después de crear y guardar una nueva fila en el formulario de presupuesto, al intentar eliminarla se producía un **error 400**.

### Síntoma:
- Error: "Request failed with status code 400"
- Ocurría al intentar eliminar filas que se habían creado y guardado recientemente
- Las filas nuevas (no guardadas) se eliminaban correctamente

## Causa del Problema

### 1. ID Incorrecto Después de Guardar
- **Causa**: Cuando se guardaba una fila nueva, se marcaba como `isNew: false` pero el ID seguía siendo el temporal (`new_${Date.now()}`)
- **Síntoma**: Al intentar eliminar, el frontend enviaba un ID que no existía en la base de datos
- **Ubicación**: `/home/desarrollo/Coofisam360-Frontend/app/modulo-financiero/tabla-presupuesto/page.js`

### 2. Lógica de Actualización de ID Faltante
- **Causa**: No se actualizaba el ID de la fila después de guardarla en la base de datos
- **Síntoma**: El ID temporal se mantenía, causando errores en operaciones posteriores
- **Resultado**: Error 400 al intentar eliminar con ID inexistente

## Flujo del Problema

### Antes de la Corrección:
1. **Crear Fila Nueva**: ID = `new_1234567890`, `isNew: true`
2. **Guardar Fila**: Se guarda en BD, se marca `isNew: false`
3. **ID Sigue Siendo**: `new_1234567890` (temporal)
4. **Intentar Eliminar**: Frontend envía DELETE con ID temporal
5. **Backend Recibe**: ID temporal que no existe en BD
6. **Resultado**: Error 400

### Después de la Corrección:
1. **Crear Fila Nueva**: ID = `new_1234567890`, `isNew: true`
2. **Guardar Fila**: Se guarda en BD
3. **Actualizar ID**: ID = `6_2025_1` (formato correcto), `isNew: false`
4. **Intentar Eliminar**: Frontend envía DELETE con ID correcto
5. **Backend Recibe**: ID válido que existe en BD
6. **Resultado**: Eliminación exitosa

## Solución Implementada

### Modificación en `handleSave`
**Archivo**: `/home/desarrollo/Coofisam360-Frontend/app/modulo-financiero/tabla-presupuesto/page.js`

```javascript
// Si es una fila nueva, actualizar el ID y marcar como no nueva
if (row.isNew) {
  const newId = `${payload.cuenta}_${payload.anio}_${payload.mes}`;
  setRows(prev =>
    prev.map(r => r.id === id ? { ...r, id: newId, isNew: false } : r)
  );
  setFilteredRows(prev =>
    prev.map(r => r.id === id ? { ...r, id: newId, isNew: false } : r)
  );
} else {
  // Si es una fila existente, solo marcar como no nueva
  setRows(prev =>
    prev.map(r => r.id === id ? { ...r, isNew: false } : r)
  );
  setFilteredRows(prev =>
    prev.map(r => r.id === id ? { ...r, isNew: false } : r)
  );
}
```

### Lógica de Actualización de ID
1. **Detectar Fila Nueva**: Verificar `row.isNew`
2. **Generar ID Correcto**: Usar formato `cuenta_anio_mes`
3. **Actualizar Estado**: Cambiar ID y marcar como no nueva
4. **Mantener Consistencia**: Actualizar tanto `rows` como `filteredRows`

## Formato de ID

### ID Temporal (Fila Nueva):
- **Formato**: `new_${Date.now()}`
- **Ejemplo**: `new_1703123456789`
- **Uso**: Solo para filas no guardadas

### ID Definitivo (Fila Guardada):
- **Formato**: `cuenta_anio_mes`
- **Ejemplo**: `6_2025_1`
- **Uso**: Para filas guardadas en la base de datos

## Validaciones Implementadas

### Frontend:
- ✅ Detección de filas nuevas vs existentes
- ✅ Actualización correcta del ID después de guardar
- ✅ Mantenimiento de consistencia en el estado
- ✅ Preservación de datos durante la transición

### Backend:
- ✅ Validación de formato de ID
- ✅ Verificación de existencia del registro
- ✅ Manejo de errores apropiado

## Comportamiento Corregido

### Antes:
- ❌ Error 400 al eliminar filas guardadas
- ❌ ID temporal se mantenía después de guardar
- ❌ Inconsistencia entre frontend y backend
- ❌ Imposibilidad de eliminar filas recién guardadas

### Después:
- ✅ Eliminación exitosa de filas guardadas
- ✅ ID se actualiza correctamente después de guardar
- ✅ Consistencia entre frontend y backend
- ✅ Funcionalidad completa de CRUD

## Flujo de Trabajo Mejorado

### 1. Crear Fila Nueva:
- ID temporal: `new_1234567890`
- Estado: `isNew: true`
- Ubicación: Principio de la tabla

### 2. Editar y Guardar:
- Datos se envían al backend
- Se guarda en la base de datos
- ID se actualiza: `6_2025_1`
- Estado: `isNew: false`

### 3. Eliminar Fila Guardada:
- Frontend envía DELETE con ID correcto
- Backend elimina de la base de datos
- Fila se remueve del estado local
- Mensaje de confirmación

## Pruebas Realizadas

### Escenario 1: Eliminar Fila Nueva (No Guardada)
- ✅ Se elimina del estado local
- ✅ No se hace petición al backend
- ✅ Confirmación doble funciona

### Escenario 2: Eliminar Fila Guardada
- ✅ Se hace petición DELETE al backend
- ✅ Se elimina de la base de datos
- ✅ Se actualiza el estado local
- ✅ Mensaje de confirmación

### Escenario 3: Transición de Nueva a Guardada
- ✅ ID se actualiza correctamente
- ✅ Estado se mantiene consistente
- ✅ Operaciones posteriores funcionan

## Resultado Final
El formulario de presupuesto ahora maneja correctamente:
- ✅ Creación de filas nuevas
- ✅ Guardado con actualización de ID
- ✅ Eliminación de filas nuevas y guardadas
- ✅ Transición fluida entre estados
- ✅ Consistencia de datos
- ✅ Experiencia de usuario sin errores


