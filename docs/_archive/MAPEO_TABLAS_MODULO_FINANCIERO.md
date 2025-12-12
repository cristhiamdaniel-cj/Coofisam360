# Mapeo de Tablas del Módulo Financiero

## Resumen Ejecutivo
Este documento mapea todas las tablas de la base de datos que están siendo utilizadas por cada formulario del módulo financiero en el frontend, incluyendo los endpoints del backend y las vistas correspondientes.

---

## 1. FORMULARIO: PRESUPUESTO
**Frontend**: `/modulo-financiero/tabla-presupuesto`
**Servicio**: `presupuesto.js`
**Endpoint**: `/api/v1/finanzas/presupuesto/`

### Tablas Utilizadas:
- **`finanzas.presupuesto`** (Principal)
  - **Campos**: `cuenta`, `anio`, `mes`, `presupuesto`, `created_at`
  - **Función**: Almacena los presupuestos por cuenta, año y mes
  - **Registros**: 848 registros disponibles

- **`plan_cuentas`** (Referencia)
  - **Campos**: `cuenta`, `nombre`
  - **Función**: Catálogo de cuentas contables para validación y autocompletado
  - **Endpoint**: `/api/v1/finanzas/cuentas-disponibles/`

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO finanzas.presupuesto`
- ✅ **READ**: `SELECT FROM finanzas.presupuesto`
- ✅ **UPDATE**: `UPDATE finanzas.presupuesto`
- ✅ **DELETE**: `DELETE FROM finanzas.presupuesto`

---

## 2. FORMULARIO: EJECUCIÓN PRESUPUESTAL (PUC 6 dígitos)
**Frontend**: `/modulo-financiero/tabla-ejecucion-presupuestal`
**Servicio**: `ejecucionPresupuestal.js`
**Endpoint**: `/api/v1/finanzas/ejecucion-presupuestal/`

### Tablas Utilizadas:
- **`finanzas.ejecucion_presupuestal_6d`** (Principal)
  - **Campos**: `id`, `anio`, `mes`, `codigo_puc6`, `nombre_rubro`, `proyectado`, `historico`, `diff_abs`, `diff_pct`, `periodo`
  - **Función**: Almacena la ejecución presupuestal con códigos PUC de 6 dígitos
  - **Registros**: 523 registros disponibles
  - **Columnas calculadas**: `diff_abs` (diferencia absoluta), `diff_pct` (diferencia porcentual)

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO finanzas.ejecucion_presupuestal_6d`
- ✅ **READ**: `SELECT FROM finanzas.ejecucion_presupuestal_6d`
- ✅ **UPDATE**: `UPDATE finanzas.ejecucion_presupuestal_6d`
- ✅ **DELETE**: `DELETE FROM finanzas.ejecucion_presupuestal_6d`

---

## 3. FORMULARIO: CUPOS DE CRÉDITO
**Frontend**: `/modulo-financiero/tabla-cupos`
**Servicio**: `creditQuota.js` + `financialService.js`
**Endpoint**: `/api/v1/finanzas/cupos-credito/`

### Tablas Utilizadas:
- **`finanzas.cupos_bancarios`** (Principal)
  - **Campos**: `id`, `entidad_financiera`, `cuentas_balance`, `fecha_renovado`, `cupo_asignado`, `cupo_ejecutado`, `disponible`, `garantia`, `utilizacion_pct`, `plazo_meses`, `tasa_pct`, `created_at`
  - **Función**: Almacena los cupos de crédito bancarios
  - **Columnas calculadas**: `disponible` (cupo_asignado - cupo_ejecutado), `utilizacion_pct` (porcentaje de utilización)

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO finanzas.cupos_bancarios`
- ✅ **READ**: `SELECT FROM finanzas.cupos_bancarios`
- ✅ **UPDATE**: `UPDATE finanzas.cupos_bancarios`
- ✅ **DELETE**: `DELETE FROM finanzas.cupos_bancarios`

---

## 4. FORMULARIO: CATEGORÍAS DE OFICINAS
**Frontend**: `/modulo-financiero/tabla-categorias`
**Servicio**: `categoriesQuota.js` + `financialService.js`
**Endpoint**: `/api/v1/finanzas/oficinas/`

### Tablas Utilizadas:
- **`finanzas.oficinas_mes`** (Principal)
  - **Campos**: `id`, `codigo_oficina`, `nombre_oficina`, `anio`, `mes_num`, `fecha_apertura`, `asociados`, `entidades_financieras`, `poblacion`, `created_at`
  - **Función**: Almacena información mensual de las oficinas por categoría
  - **Endpoint detalle**: `/api/v1/finanzas/oficinas/{codigo}/`

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO finanzas.oficinas_mes`
- ✅ **READ**: `SELECT FROM finanzas.oficinas_mes`
- ✅ **UPDATE**: `UPDATE finanzas.oficinas_mes`
- ✅ **DELETE**: `DELETE FROM finanzas.oficinas_mes`

---

## 5. FORMULARIO: INDICADORES FINANCIEROS
**Frontend**: `/modulo-financiero/tabla-indicadores`
**Servicio**: `indicatorsQuota.js` + `financialService.js`
**Endpoint**: `/api/v1/indicadores/comparativa/`

### Tablas Utilizadas:
- **`indicadores.indicadores_comparativa`** (Principal)
  - **Campos**: `id`, `codigo`, `anio`, `mes`, `periodo`, `nombre_indicador`, `alcance`, `valor_indicador`, `anio_menos_1_dic`, `valor_indicador_2`, `mes_anterior`, `valor_indicador_3`, `mismo_mes_anio_anterior`, `valor_indicador_4`, `diciembre_anio_anterior`, `valor_indicador_5`, `analisis`, `created_at`
  - **Función**: Almacena indicadores financieros con comparativas históricas
  - **Endpoint auxiliar**: `/api/v1/indicadores/disponibles/`

- **`indicadores.cat_indicador`** (Referencia)
  - **Función**: Catálogo de indicadores disponibles
  - **Endpoint**: `/api/v1/indicadores/disponibles/`

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO indicadores.indicadores_comparativa`
- ✅ **READ**: `SELECT FROM indicadores.indicadores_comparativa`
- ✅ **UPDATE**: `UPDATE indicadores.indicadores_comparativa`
- ✅ **DELETE**: `DELETE FROM indicadores.indicadores_comparativa`

---

## 6. FORMULARIO: ANÁLISIS EXPLICATIVO
**Frontend**: `/modulo-financiero/tabla-analisis`
**Servicio**: `analisisExplicativo.js`
**Endpoint**: `/api/v1/analisis/explicativo/`

### Tablas Utilizadas:
- **`indicadores.analisis_explicativo`** (Principal)
  - **Campos**: `id`, `anio`, `mes`, `categoria`, `subcategoria`, `descripcion`, `created_at`, `updated_at`
  - **Función**: Almacena análisis explicativos por categoría y subcategoría
  - **Endpoint detalle**: `/api/v1/analisis/explicativo/{id}/`

### Operaciones CRUD:
- ✅ **CREATE**: `INSERT INTO indicadores.analisis_explicativo`
- ✅ **READ**: `SELECT FROM indicadores.analisis_explicativo`
- ✅ **UPDATE**: `UPDATE indicadores.analisis_explicativo`
- ✅ **DELETE**: `DELETE FROM indicadores.analisis_explicativo`

---

## 7. FORMULARIO: CARGA DE BALANCE
**Frontend**: `/modulo-financiero/carga-balance`
**Función**: Carga de archivos Excel/CSV del Libro de Balance

### Tablas Utilizadas:
- **`finanzas.saldos_consolidados`** (Destino)
  - **Función**: Almacena los saldos consolidados del Libro de Balance
  - **Proceso**: ETL desde archivos Excel/CSV

---

## 8. FORMULARIO: ETL
**Frontend**: `/modulo-financiero/etl`
**Función**: Procesos de Extracción, Transformación y Carga

### Tablas Utilizadas:
- **Múltiples tablas de cálculo**:
  - `indicadores.calc_*` (49 tablas de cálculo)
  - `indicadores.saldos_consolidados_mensuales`
  - `indicadores.valores_indicadores`
  - `indicadores.resultados`

---

## Esquemas de Base de Datos Utilizados

### 1. Esquema `finanzas`
- `presupuesto` - Presupuestos por cuenta
- `ejecucion_presupuestal_6d` - Ejecución presupuestal PUC 6 dígitos
- `cupos_bancarios` - Cupos de crédito bancarios
- `oficinas_mes` - Información mensual de oficinas
- `saldos_consolidados` - Saldos consolidados del balance
- `cuentas_financieras` - Cuentas financieras
- `indicadores_calculados` - Indicadores calculados

### 2. Esquema `indicadores`
- `analisis_explicativo` - Análisis explicativos
- `indicadores_comparativa` - Indicadores con comparativas
- `cat_indicador` - Catálogo de indicadores
- `calc_*` - 49 tablas de cálculo de indicadores
- `saldos_consolidados_mensuales` - Saldos mensuales consolidados
- `valores_indicadores` - Valores de indicadores
- `resultados` - Resultados de cálculos

### 3. Esquema `oficinas`
- `categorias` - Categorías de oficinas
- `datos_mensuales_oficinas` - Datos mensuales de oficinas
- `clasificacion_categorias_mensual` - Clasificación mensual
- `oficinas_info_adicional` - Información adicional

### 4. Esquema `public`
- `plan_cuentas` - Plan de cuentas contables
- `cupos_credito_form` - Formulario de cupos de crédito
- `cupos_credito_hist` - Histórico de cupos de crédito
- `fact_categorias_oficinas` - Hechos de categorías de oficinas
- `fact_indicador_sub_analisis` - Hechos de análisis de indicadores
- `fact_oficina_indicadores` - Hechos de indicadores de oficinas
- `indicadores_alcance` - Alcance de indicadores
- `indicadores_interpretacion` - Interpretación de indicadores

---

## Endpoints del Backend

### Finanzas
- `GET/POST /api/v1/finanzas/presupuesto/` - Presupuesto
- `GET/POST /api/v1/finanzas/ejecucion-presupuestal/` - Ejecución presupuestal
- `GET/POST /api/v1/finanzas/cupos-credito/` - Cupos de crédito
- `GET/POST /api/v1/finanzas/oficinas/` - Oficinas
- `GET /api/v1/finanzas/cuentas-disponibles/` - Cuentas disponibles

### Indicadores
- `GET/POST /api/v1/indicadores/comparativa/` - Indicadores comparativos
- `GET /api/v1/indicadores/disponibles/` - Indicadores disponibles

### Análisis
- `GET/POST/PUT/DELETE /api/v1/analisis/explicativo/` - Análisis explicativo

---

## Vistas del Backend

### Clases APIView
- `PresupuestoView` - Maneja presupuesto
- `EjecucionPresupuestalView` - Maneja ejecución presupuestal
- `CuposCreditoView` - Maneja cupos de crédito
- `OficinasView` - Maneja oficinas
- `AnalisisExplicativoView` - Maneja análisis explicativo
- `IndicadoresAnalisisView` - Maneja análisis de indicadores

### Funciones API
- `cuentas_disponibles` - Lista cuentas del plan de cuentas
- `indicadores_comparativa` - Lista indicadores comparativos
- `indicadores_disponibles` - Lista indicadores disponibles

---

## Resumen de Registros por Tabla

| Tabla | Registros | Formulario |
|-------|-----------|------------|
| `finanzas.presupuesto` | 848 | Presupuesto |
| `finanzas.ejecucion_presupuestal_6d` | 523 | Ejecución Presupuestal |
| `finanzas.cupos_bancarios` | Variable | Cupos de Crédito |
| `finanzas.oficinas_mes` | Variable | Categorías de Oficinas |
| `indicadores.indicadores_comparativa` | Variable | Indicadores Financieros |
| `indicadores.analisis_explicativo` | Variable | Análisis Explicativo |
| `plan_cuentas` | Variable | Referencia (Presupuesto) |

---

## Notas Técnicas

### Configuración de Servicios
- **Servicios que funcionan**: Usan `import api from "../api"` (patrón estándar)
- **Servicios problemáticos**: Usaban configuración personalizada de axios
- **Solución aplicada**: Unificación de patrones para todos los servicios

### Autenticación
- **Token**: `ff6c34cf9e07b35bd5a26f65cdb356ed00ce7c47` (fallback)
- **Método**: `Authorization: Token {token}`
- **Almacenamiento**: `localStorage.getItem('authToken')`

### CORS
- **Configuración**: `CORS_ALLOW_ALL_ORIGINS = True` (desarrollo)
- **Orígenes permitidos**: localhost, ngrok, dominios externos
- **Credenciales**: `CORS_ALLOW_CREDENTIALS = True`

---

## Conclusión

El módulo financiero utiliza **7 formularios principales** que interactúan con **más de 60 tablas** distribuidas en **4 esquemas** de base de datos. Cada formulario tiene su propia tabla principal y puede referenciar tablas auxiliares para validación y catálogos.

La arquitectura sigue un patrón consistente de:
1. **Frontend** (React/Next.js)
2. **Servicios** (JavaScript)
3. **API Backend** (Django REST Framework)
4. **Base de Datos** (PostgreSQL)

Todos los formularios ahora usan el mismo patrón de servicios, lo que garantiza consistencia y mantenibilidad.


