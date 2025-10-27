# Carga de Datos: Ejecución Presupuestal PUC 6 dígitos

## Resumen
Se cargaron exitosamente **523 registros** de datos de ejecución presupuestal para agosto 2025 en la tabla `finanzas.ejecucion_presupuestal_6d`.

## Archivo de Datos
- **Archivo**: `/home/desarrollo/coofisam360/datos_presupuesto.txt`
- **Tamaño**: 299KB, 3,140 líneas
- **Formato**: SQL con INSERT statements
- **Período**: Agosto 2025 (mes=8, año=2025)

## Problemas Encontrados y Solucionados

### 1. Error de Precisión Numérica
**Problema**: 
```
ERROR: numeric field overflow
DETAIL: A field with precision 7, scale 4 must round to an absolute value less than 10^3.
```

**Causa**: La columna `diff_pct` tenía precisión NUMERIC(7,4), limitando valores a 999.9999%

**Solución**:
```sql
ALTER TABLE finanzas.ejecucion_presupuestal_6d 
ALTER COLUMN diff_pct TYPE NUMERIC(15,4);
```

### 2. Transacción Sin COMMIT
**Problema**: El archivo SQL no tenía `COMMIT;` al final, causando que la transacción se revirtiera

**Solución**: Se agregó `COMMIT;` al final del archivo

## Estructura de Datos Cargados

### Tabla: `finanzas.ejecucion_presupuestal_6d`
- **Registros cargados**: 523
- **Período**: Agosto 2025
- **Campos principales**:
  - `anio`: 2025
  - `mes`: 8
  - `codigo_puc6`: Código PUC de 6 dígitos
  - `nombre_rubro`: Nombre del rubro contable
  - `proyectado`: Valor proyectado
  - `historico`: Valor histórico
  - `diff_abs`: Diferencia absoluta (calculada)
  - `diff_pct`: Diferencia porcentual (calculada)

### Ejemplos de Datos Cargados:
```
Código PUC6: 000001 - ACTIVO
- Proyectado: $257,374,405,566.00
- Histórico: $279,851,309,569.00
- Diferencia: -$22,476,904,003.00 (-8.73%)

Código PUC6: 000002 - PASIVOS
- Proyectado: $181,147,161,887.00
- Histórico: $200,678,785,950.00
- Diferencia: -$19,531,624,063.00 (-10.78%)

Código PUC6: 000003 - PATRIMONIO
- Proyectado: $76,267,284,809.00
- Histórico: $79,172,523,619.00
- Diferencia: -$2,905,238,810.00 (-3.81%)
```

## Verificación de la Carga

### 1. Conteo de Registros:
```sql
SELECT COUNT(*) FROM finanzas.ejecucion_presupuestal_6d 
WHERE anio = 2025 AND mes = 8;
-- Resultado: 523 registros
```

### 2. Muestra de Datos:
```sql
SELECT codigo_puc6, nombre_rubro, proyectado, historico, diff_abs, diff_pct 
FROM finanzas.ejecucion_presupuestal_6d 
WHERE anio = 2025 AND mes = 8 
ORDER BY codigo_puc6 LIMIT 10;
```

### 3. Verificación de API:
```bash
curl -X GET "http://localhost:8060/api/v1/finanzas/ejecucion-presupuestal/?anio=2025&mes=8&limit=5" \
  -H "Authorization: Token ff6c34cf9e07b35bd5a26f65cdb356ed00ce7c47"
```

**Resultado**: API funcionando correctamente, devuelve datos en formato JSON

## Campos Calculados Automáticamente

### 1. Diferencia Absoluta (`diff_abs`):
```sql
diff_abs = proyectado - historico
```

### 2. Diferencia Porcentual (`diff_pct`):
```sql
diff_pct = CASE
    WHEN proyectado = 0 THEN NULL
    ELSE ROUND(((proyectado - historico) / proyectado) * 100, 4)
END
```

### 3. Período (`periodo`):
```sql
periodo = MAKE_DATE(anio, mes, 1)
```

## Categorías de Datos Cargados

### Principales Rubros:
- **ACTIVO**: $257,374,405,566.00 proyectado
- **PASIVOS**: $181,147,161,887.00 proyectado
- **PATRIMONIO**: $76,267,284,809.00 proyectado
- **INGRESOS**: $30,630,243,287.00 proyectado
- **GASTOS**: $25,150,360,803.00 proyectado

### Subcategorías Incluidas:
- Efectivo y equivalente al efectivo
- Inversiones
- Cartera de créditos
- Cuentas por cobrar
- Costo de ventas
- Y más de 500 rubros adicionales

## Integridad de Datos

### Restricciones Aplicadas:
- **Clave única**: `(anio, mes, codigo_puc6)`
- **ON CONFLICT**: Actualización automática si existe duplicado
- **Validación**: Códigos PUC6 de 6 dígitos
- **Precisión**: Valores numéricos con 2 decimales

### Validaciones Realizadas:
- ✅ Todos los registros tienen códigos PUC6 válidos
- ✅ Valores numéricos correctamente formateados
- ✅ Cálculos automáticos funcionando
- ✅ API respondiendo correctamente
- ✅ No hay duplicados

## Acceso a los Datos

### 1. Consulta Directa a Base de Datos:
```sql
SELECT * FROM finanzas.ejecucion_presupuestal_6d 
WHERE anio = 2025 AND mes = 8;
```

### 2. API REST:
```bash
# Obtener todos los registros de agosto 2025
GET /api/v1/finanzas/ejecucion-presupuestal/?anio=2025&mes=8

# Obtener con paginación
GET /api/v1/finanzas/ejecucion-presupuestal/?anio=2025&mes=8&limit=50&offset=0

# Filtrar por código PUC6
GET /api/v1/finanzas/ejecucion-presupuestal/?anio=2025&mes=8&codigo_puc6=000001
```

### 3. Frontend:
Los datos están disponibles en el formulario "Ejecución Presupuestal PUC 6 dígitos" del módulo financiero.

## Próximos Pasos

### 1. Verificación en Frontend:
- Acceder al formulario de ejecución presupuestal
- Verificar que los datos se muestran correctamente
- Probar funcionalidades de filtrado y búsqueda

### 2. Análisis de Datos:
- Revisar diferencias significativas entre proyectado e histórico
- Identificar rubros con mayores variaciones
- Generar reportes de análisis

### 3. Mantenimiento:
- Establecer proceso de carga regular
- Documentar procedimientos de actualización
- Configurar alertas para variaciones significativas

## Conclusión

La carga de datos fue **exitosa** con:
- ✅ **523 registros** cargados correctamente
- ✅ **Estructura de datos** validada
- ✅ **API funcionando** correctamente
- ✅ **Cálculos automáticos** operativos
- ✅ **Integridad de datos** mantenida

Los datos están listos para ser utilizados en el sistema de gestión financiera y análisis presupuestal.


