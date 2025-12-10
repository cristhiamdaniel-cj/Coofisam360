# 01 · Informe de Base de Datos — Módulo Financiero (Power BI)

Este documento describe las **vistas** que consumen los tableros de **Power BI** del módulo financiero de **Coofisam360**.
Incluye su **propósito**, **columnas expuestas**, **fuentes/dependencias**, **reglas de negocio** y **notas de rendimiento/validación**.

> Cobertura:
>
> * vistas de indicadores por oficina y comparativas
> * vistas “6 meses flat” por cuentas clave
> * vistas de presupuesto y cupos
> * vistas de saldos con variación y de categorías/oficina
> * matriz de oficinas (pivote + scoring)
> * placeholders para vistas de calendario / auxiliares

---

## 0. Resumen ejecutivo (inventario de vistas)

| Vista (schema.nombre)                              | Propósito principal                                                                                              |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **finanzas.vista\_cupos\_bancarios**               | Exponer cupos, ejecución, disponible, tasa y plazo por entidad para visualizaciones y tablas.                    |
| **indicadores.matriz\_oficinas**                   | Pivotea indicadores por oficina/mes y calcula **puntajes** y **clasificación** (Bajo/Medio/Bueno/Muy Bueno).     |
| **indicadores.vista\_indicadores\_comparativa**    | Comparativa del indicador vs dic-1, mismo mes año -1 y -2; base para gráficos de tendencia y análisis año-a-año. |
| **indicadores.vista\_indicadores\_por\_oficina**   | Cálculo mensual de indicadores **genéricos** por oficina usando `indicadores.calcular_indicador_generico(...)`.  |
| **indicadores.vista\_presupuesto\_mensual**        | Presupuesto mensual por cuenta con nombre de cuenta y **periodo** `YYYY-MM`.                                     |
| **public.vista\_saldos\_con\_variacion**           | Saldos agregados por cuenta/oficina con **variación mensual** y **variación anual** (% y absolutos).             |
| **public.vista\_cuenta2/3/4/5/6/14\_6meses\_flat** | Serie **“6 meses en columnas”** por cuenta para tarjetas/mini-trends (mes actual y 5 meses atrás).               |
| **public.vista\_cuenta980000\_6meses\_flat**       | Igual a las “6 meses” pero para **999999/980000** (resultados acumulados y especiales).                          |
| **public.vista\_cuenta999999\_6meses\_flat**       | Idem anterior (otra cuenta especial).                                                                            |
| **public.vista\_oficina\_categorias**              | Atributos de oficina (cartera, depósitos, asociados, población, etc.) por mes/año.                               |
| **public.vista\_oficina\_indicadores**             | Indicadores por oficina (texto, % y puntos), **normaliza** nombre de indicador sin sufijos.                      |
| **T\_Calendario** *(placeholder)*                  | Tabla de fechas/categorías calendarias para segmentación temporal.                                               |
| **g\_matriz\_oficina** *(placeholder)*             | Vista auxiliar (si aplica) para agregados por oficina/periodo (pendiente adjuntar SQL).                          |

---

## 1) finanzas.vista\_cupos\_bancarios

**Propósito**
Listado listo-para-reporte de **cupos** por entidad con campos normalizados para presentación.

**Columnas clave (alias de salida)**

* `FECHA RENOVADO`, `ENTIDAD FINANCIERA`, `CUPO ASIGNADO`, `CUPO EJECUTADO` (texto con `' - '` si nulo/0), `DISPONIBLE`
* `GARANTIA`, `% Utilización` (COALESCE a 0), `PLAZO/MESES` (texto o NULL), `TASA` (concatena `%` o “La vigente al desembolso”)
* `CUENTAS BALANCE` (NULL si `'SIN_ESPECIFICAR'`)

**Origen/Dependencias**

* `finanzas.cupos_bancarios`

**Reglas/Transformaciones**

* Normalización de nulos a `' - '` y casting a texto para **presentación**.
* Ordenado por `entidad_financiera`.

**Validación / Calidad de datos**

* Verificar `% Utilización` ∈ \[0,1] o \[0,100] según definición. Si está en fracción, formatear en Power BI como porcentaje.
* `CUPO EJECUTADO` como texto: si se requiere numérico en el modelo semántico, crear medida DAX o duplicar campo numérico.

**Rendimiento/Índices**

* Índice sugerido en la tabla base por `(entidad_financiera)` si el volumen crece.

---

## 2) indicadores.matriz\_oficinas

**Propósito**
Construye, por **oficina/mes**, un **pivot** de indicadores y luego calcula **puntajes** y un **resultado cualitativo**. Es la base para un **ranking de oficinas**.

**Columnas destacadas**

* % indicadores: `pct_calidad_cartera`, `pct_margen_operacional`, `pct_margen_neto`, etc.
* Puntos: `pts_*` por indicador con **reglas de tramos** (thresholds).
* `Puntos` (suma de todos los puntos) y `Resultado` (Bajo/Medio/Bueno/Muy Bueno) según rangos de la suma.

**Origen/Dependencias**

* `indicadores.vw_matriz_oficinas` (fuente pivot)
* `oficinas` (join por código)

**Reglas/Transformaciones**

* `max(CASE WHEN codigo_indicador = ... THEN valor_calculado)` para pivot.
* Reglas de puntaje por **umbrales** fijos (documentados en el SQL).
* Clasificación final por rangos de la **suma de puntos**.

**Notas de negocio**

* Revisar periódicamente los **umbrales**; están codificados en SQL (mantenimiento requiere cambio en vista).
* Las métricas son porcentajes y requieren formato en Power BI.

**Rendimiento**

* Crear **vista materializada** o **tabla intermedia** si el pivot se vuelve pesado.
* Índices en `vw_matriz_oficinas` por `(oficina, anio, mes, codigo_indicador)`.

---

## 3) indicadores.vista\_indicadores\_comparativa

**Propósito**
Comparar un **indicador** con:

* **Diciembre del año anterior**
* **Mismo mes del año anterior**
* **Mismo mes de hace dos años**

**Columnas clave**

* `mes`, `anio`, `periodo` (`YYYY-MM`)
* `nombre_indicador`, `valor_indicador` (actual)
* `valor_indicador_2` (dic-1), `valor_indicador_3` (mismo mes a-1), `valor_indicador_4` (mismo mes a-2)
* Campos de referencia textual (e.g., `mismo_mes_ref_1/2`)

**Origen**

* `indicadores.vista_indicadores_consolidados` (múltiples self-joins con offsets de año)

**Reglas**

* Construcción de `periodo` con `lpad(mes,2,'0')`.
* Joins por `codigo_indicador`, `anio`/`mes` desplazados.

**Validación / QA**

* Asegurar **completitud** de series (si faltan meses, pueden aparecer nulos). Tratar nulos en PBI con COALESCE/DAX.
* Confirmar si los indicadores vienen **homogéneos** (mismo cálculo a través de años).

---

## 4) indicadores.vista\_indicadores\_por\_oficina

**Propósito**
Genera el **valor calculado** por **indicador** y **oficina**, por cada mes disponible en `saldos_agencia`.

**Columnas**

* `codigo_indicador`, `nombre_indicador`, `categoria`, `tipo_calculo`
* `agencia_codigo`, `oficina`, `anio`, `mes`, `nombre_mes`, `periodo`
* `valor_calculado` (via `indicadores.calcular_indicador_generico(...)`)

**Origen/Dependencias**

* `indicadores.indicadores_financieros` (estado = 'Activo', `ambito_calculo` ∈ {'oficina','ambos'})
* `oficinas`, `saldos_agencia` (fechas distintas)

**Reglas**

* **CROSS JOIN** con universo de meses disponibles; cuidado con granularidad (puede explotar filas).
* Orden: `codigo_indicador`, `oficina`, `anio`, `mes`.

**Rendimiento**

* Índices en `saldos_agencia(anio,mes)` y `oficinas(codigo)`.
* Considerar **materializar** por corte mensual si el cálculo es costoso.

---

## 5) indicadores.vista\_presupuesto\_mensual

**Propósito**
Exponer **presupuesto** mensual por **cuenta** con su nombre y `periodo`.

**Columnas**

* `cuenta`, `nombre_cuenta`, `mes` (nombre), `anio`, `presupuesto`, `mes_numero`, `periodo`

**Origen**

* `finanzas.presupuesto` + `plan_cuentas`

**Reglas**

* Diccionario de meses (CASE 1..12) → `mes`.
* `periodo = anio || '-' || lpad(mes,2,'0')`.

**Validación**

* Integridad referencial `presupuesto.cuenta` ↔ `plan_cuentas.cuenta`.
* Unicidad esperada por `(cuenta, anio, mes)`.

---

## 6) public.vista\_saldos\_con\_variacion

**Propósito**
Base **agregada** por cuenta/oficina/mes con **variación mensual** y **variación interanual**.

**Columnas clave**

* `id_cuenta`, `nombre_cuenta`, `oficina`, `anio`, `mes`, `nombre_mes`, `fecha_texto`
* `saldo_total`, `saldo_mes_anterior`, `variacion`, `variacion_porcentaje`
* `saldo_mismo_mes_anio_anterior`, `variacion_anual`, `variacion_anual_porcentaje`

**Origen**

* Agregaciones sobre `saldos_agencia` + `plan_cuentas` + `oficinas`

**Reglas**

* Join **mes anterior** con lógica de rollover (dic→ene).
* Join **mismo mes año pasado** (anio-1).
* `%` calculados con protección de división por cero.

**Rendimiento**

* Índices útiles: `saldos_agencia(cuenta, agencia_codigo, anio, mes)`; `oficinas(codigo)`
* Posible **materialización** por corte mensual.

---

## 7) Vistas “6 meses flat” por cuenta

**Objetivo**
Proveer una **estructura en columnas** para tarjetas y comparaciones rápidas (mes actual y 5 previos).

**Conjunto**

* `public.vista_cuenta2_6meses_flat`
* `public.vista_cuenta3_6meses_flat` *(combina cuenta 3 + 980000 → “Patrimonio + Resultados”)*
* `public.vista_cuenta4_6meses_flat`
* `public.vista_cuenta5_6meses_flat`
* `public.vista_cuenta6_6meses_flat`
* `public.vista_cuenta14_6meses_flat`
* `public.vista_cuenta980000_6meses_flat`
* `public.vista_cuenta999999_6meses_flat`

**Columnas (patrón)**

* `id_cuenta`, `nombre_cuenta`, `oficina`
* `fecha_actual`, `saldo_total_actual`
* `fecha_menos_1` … `fecha_menos_5`
* `saldo_total_menos_1` … `saldo_total_menos_5`

**Origen**

* Todas se derivan de `public.vista_saldos_con_variacion` filtrando por `id_cuenta` y re-uniendo por desplazamientos de `1..5` meses.

**Reglas**

* Filtro `make_date(anio,mes,1) >= '2020-01-01'`.
* En la variante **cuenta3**, se hace **FULL JOIN** con cuenta `980000` y se **suman** saldos → `id_cuenta = '3+980000'`.

**Uso en Power BI**

* Excelente para **small multiples**, tarjetas KPI y comparadores de tendencia corta.
* Si se requiere **más de 6 meses**, considerar una versión **dinámica** (filas) + medida DAX.

**Rendimiento**

* Índices sobre `vista_saldos_con_variacion(oficina, anio, mes, id_cuenta)` o materialización.

---

## 8) public.vista\_oficina\_categorias

**Propósito**
Atributos estructurales por **oficina/mes**: cartera, depósitos, asociados, población, etc.

**Columnas**

* `codigo` (oficina), `oficina_nombre`, `anio`, `mes`
* `cartera_de_credito`, `depositos`, `asociados`, `fecha_de_apertura`, `entidades_financieras`, `poblacion`

**Origen**

* `fact_categorias_oficinas` + `oficinas`

**Notas**

* Útil para segmentar (slicers) y enriquecer vistas de desempeño por contexto.

---

## 9) public.vista\_oficina\_indicadores

**Propósito**
Consolida **indicadores por oficina/mes** en tres tipos de valor: `%`, **puntos** y **texto**, y **limpia** el nombre del indicador.

**Columnas**

* `oficina_codigo`, `oficina_nombre`, `anio`, `mes`, `indicador` *(regex: quita “(Puntos|%|Resultado)”)*
* `valor_pct` *(se multiplica por 10,000 en SQL; revisar formato en PBI)*
* `valor_puntos`, `valor_texto`

**Origen**

* `fact_oficina_indicadores` + `oficinas` + `fechas` + `indicadores`

**Notas**

* Verificar si `valor_pct` está **escalado** (×100 o ×10000) y normalizar formato final en Power BI.

---

## 10) Placeholders / Auxiliares

### T\_Calendario

**Propósito**: Tabla de fechas para usar en rel. 1:\* con hechos y permitir **inteligencia de tiempo** (YTD, YoY, MTD).
**Recomendación mínima**:

* Columnas: `Fecha` (date, PK), `Año`, `Mes`, `NombreMes`, `Periodo` (`YYYY-MM`), `Trimestre`, `EsFinDeMes`
* Rango: cubrir **todo el histórico** de `saldos_agencia` y **proyecciones** si aplica.
  *(Adjuntar SQL al integrarlo.)*

### g\_matriz\_oficina

**Propósito**: Si existe como vista intermedia para agregados de oficina, documentar su definición y relaciones con `indicadores.matriz_oficinas`.
*(Pendiente adjuntar definición SQL.)*

---

## 11) Lineamientos de modelado (para Power BI)

1. **Claves de relación**

   * Usar `Periodo (YYYY-MM)` o `Fecha` contra `T_Calendario`.
   * `oficinas`: relacionar por `codigo` ↔ `agencia_codigo` / `oficina_codigo`.

2. **Formato de medidas**

   * Establecer `%` como **decimal** con formato porcentaje.
   * Campos tipo texto en vistas (p.ej., `CUPO EJECUTADO`) deben tener **par** numérico si se usará agregación.

3. **Conformidad temporal**

   * Asegurar presencia de todos los meses en `T_Calendario` aunque no existan datos; usar **left join** desde calendario en PBI si se desea mostrar ceros.

4. **Rendimiento**

   * Considerar **vistas materializadas** para: `matriz_oficinas`, `vista_saldos_con_variacion` y “6 meses flat”.
   * Indexar tablas base: `saldos_agencia(cuenta, agencia_codigo, anio, mes)`, `presupuesto(cuenta, anio, mes)`.

5. **Gobernanza**

   * Congelar definiciones de **umbrales** de puntajes en un **catálogo** externo (tabla parametrizable) para evitar cambios de código en vistas.

---

## 12) Checks de calidad (antes de publicar)

* [ ] `saldos_agencia`: sin **meses faltantes** para cuentas clave (2,3,4,5,6,14,980000,999999).
* [ ] `indicadores_*`: mismas **definiciones** y **signos** a través de años.
* [ ] `vista_oficina_indicadores.valor_pct`: validar **escala** y formato.
* [ ] `vista_cupos_bancarios`: `% Utilización` consistente; sin texto en campos que requieran suma/promedio.
* [ ] `vista_presupuesto_mensual`: unicidad `(cuenta, anio, mes)` garantizada.
* [ ] Relaciones en PBI revisadas: calendario ↔ hechos, oficinas ↔ hechos.

---

## 13) Consultas de ejemplo (útiles para debugging)

```sql
-- 1) Validar series mensuales por cuenta en saldos_con_variacion
SELECT id_cuenta, oficina, anio, mes, saldo_total
FROM public.vista_saldos_con_variacion
WHERE id_cuenta IN ('2','3','4','5','6','14','980000','999999')
ORDER BY id_cuenta, oficina, anio, mes;

-- 2) Top oficinas por “Puntos” de matriz_oficinas
SELECT nombre_oficina, anio, mes, "Puntos", "Resultado"
FROM indicadores.matriz_oficinas
ORDER BY anio DESC, mes DESC, "Puntos" DESC
LIMIT 50;

-- 3) Indicador específico: comparativa histórica
SELECT *
FROM indicadores.vista_indicadores_comparativa
WHERE nombre_indicador = '<<NOMBRE_INDICADOR>>'
ORDER BY anio DESC, periodo DESC;

-- 4) Cuadrito 6 meses para cuenta 3+980000 (patrimonio+resultados)
SELECT *
FROM public.vista_cuenta3_6meses_flat
WHERE oficina = '<<NOMBRE_OFICINA>>'
ORDER BY fecha_actual DESC
LIMIT 12;
```

---
