from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from django.db import connections, transaction
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


@dataclass
class FilterContext:
    where: list[str]
    params: dict[str, Any]


IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$", re.IGNORECASE)


def quote_identifier(identifier: str) -> str:
    if IDENTIFIER_RE.match(identifier):
        return identifier
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def strip_accents_upper(value: str) -> str:
    if value is None:
        return ""
    s = str(value).upper()
    # Reemplazos básicos para español
    return (
        s.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ü", "U")
        .replace("Ñ", "N")
    )


MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


def month_to_int(value: Any) -> int:
    if value is None:
        raise ValueError("El mes no puede ser nulo")
    if isinstance(value, int):
        if 1 <= value <= 12:
            return value
        raise ValueError("El mes numérico debe estar entre 1 y 12")
    raw = str(value).strip()
    if not raw:
        raise ValueError("El mes no puede estar vacío")
    if raw.isdigit():
        num = int(raw)
        if 1 <= num <= 12:
            return num
        raise ValueError("El mes numérico debe estar entre 1 y 12")
    normalized = re.sub(r"\s+", " ", raw).upper()
    normalized = normalized.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    normalized = normalized.replace(" DE", "").strip()
    if normalized in MONTHS:
        return MONTHS[normalized]
    raise ValueError(f"Mes desconocido: {value}")


def int_to_month_es(value: int) -> str:
    for name, num in MONTHS.items():
        if num == value:
            return name
    raise ValueError(f"Mes inválido: {value}")


def parse_date_value(value: Any) -> date:
    if value is None:
        raise ValueError("La fecha no puede ser nula")
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        raise ValueError("La fecha no puede estar vacía")
    if len(raw) == 7 and re.match(r"^\d{4}-\d{2}$", raw):
        raw = f"{raw}-01"
    if len(raw) == 6 and re.match(r"^\d{4}\d{2}$", raw):
        raw = f"{raw[:4]}-{raw[4:]}-01"
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError as exc:
        raise ValueError(f"Formato de fecha inválido: {value}") from exc


def build_periodo(anio: Any, mes: Any) -> date:
    if anio is None or mes is None:
        raise ValueError("Se requieren 'anio' y 'mes' para construir el periodo")
    try:
        anio_int = int(anio)
    except (TypeError, ValueError) as exc:
        raise ValueError("El año debe ser numérico") from exc
    mes_int = month_to_int(mes)
    return date(anio_int, mes_int, 1)


def cast_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (float, int)):
        return Decimal(str(value))
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw.replace("%", "").replace("$", "").replace(" ", "")
    # Detect formato con separador de miles y decimal latino ("1.234,56")
    if "," in normalized and normalized.count(".") >= 1:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif normalized.count(",") == 1 and normalized.count(".") == 0:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Valor numérico inválido: {value}") from exc


def cast_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    return raw in {"1", "true", "t", "yes", "y", "si", "sí"}


def cast_value(field_type: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        value = stripped
    if field_type in {"int", "smallint", "bigint"}:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Valor entero inválido") from exc
    if field_type in {"numeric", "decimal", "float"}:
        return cast_decimal(value)
    if field_type == "date":
        return parse_date_value(value)
    if field_type == "upper_text":
        return str(value).strip().upper()
    if field_type == "text":
        return str(value)
    if field_type == "bool":
        return cast_bool(value)
    return value


def filter_equals(column: str, cast: str | None = None, upper: bool = False) -> Callable[[str, FilterContext], None]:
    def _apply(raw: str, ctx: FilterContext) -> None:
        value: Any = raw
        if cast:
            value = cast_value(cast, value)
        if upper and isinstance(value, str):
            value = value.upper()
        param_key = f"p_{len(ctx.params)}"
        ctx.params[param_key] = value
        ctx.where.append(f"{column} = %({param_key})s")
    return _apply


def filter_period_year(column: str = "periodo") -> Callable[[str, FilterContext], None]:
    def _apply(raw: str, ctx: FilterContext) -> None:
        value = cast_value("int", raw)
        param_key = f"p_{len(ctx.params)}"
        ctx.params[param_key] = value
        ctx.where.append(f"EXTRACT(YEAR FROM {column}) = %({param_key})s")
    return _apply


def filter_period_month(column: str = "periodo") -> Callable[[str, FilterContext], None]:
    def _apply(raw: str, ctx: FilterContext) -> None:
        value = month_to_int(raw)
        param_key = f"p_{len(ctx.params)}"
        ctx.params[param_key] = value
        ctx.where.append(f"EXTRACT(MONTH FROM {column}) = %({param_key})s")
    return _apply


def filter_ilike(column: str) -> Callable[[str, FilterContext], None]:
    def _apply(raw: str, ctx: FilterContext) -> None:
        value = str(raw).strip()
        if not value:
            return
        param_key = f"p_{len(ctx.params)}"
        ctx.params[param_key] = f"%{value}%"
        ctx.where.append(f"{column} ILIKE %({param_key})s")
    return _apply


def sql_normalize_es(column_sql: str) -> str:
    # Normaliza a mayúsculas y quita tildes para comparaciones más tolerantes
    return (
        "translate(upper(" + column_sql + "), 'ÁÉÍÓÚÜÑ', 'AEIOUUN')"
    )


STOPWORDS_TOK = {"EL", "LA", "LOS", "LAS", "DE", "DEL", "Y"}


def filter_contains_tokens_normalized(column_sql: str, extra_stopwords: set[str] | None = None) -> Callable[[str, FilterContext], None]:
    norm_expr = sql_normalize_es(column_sql)
    extra = extra_stopwords or set()

    def _apply(raw: str, ctx: FilterContext) -> None:
        txt = strip_accents_upper(raw)
        tokens = [t for t in re.split(r"\s+", re.sub(r"[^A-Z0-9]+", " ", txt)) if t]
        tokens = [t for t in tokens if t not in STOPWORDS_TOK and t not in extra]
        if not tokens:
            return
        parts: list[str] = []
        for t in tokens:
            pkey = f"tok_{len(ctx.params)}"
            ctx.params[pkey] = f"%{t}%"
            parts.append(f"{norm_expr} LIKE %({pkey})s")
        ctx.where.append(" AND ".join(parts))

    return _apply


def parse_ascensos_id(raw: str, ctx: FilterContext) -> None:
    parts = str(raw).split("-")
    if len(parts) < 3:
        return
    anio_raw, mes_raw, oficina_raw = parts[0], parts[1], parts[2]
    periodo = build_periodo(anio_raw, mes_raw)
    param_periodo = f"periodo_{len(ctx.params)}"
    ctx.params[param_periodo] = periodo
    ctx.where.append(f"periodo = %({param_periodo})s")
    oficina_key = f"oficina_{len(ctx.params)}"
    ctx.params[oficina_key] = cast_value("int", oficina_raw)
    ctx.where.append(f"oficina_codigo = %({oficina_key})s")


def parse_simple_composite_id(pk_fields: list[str]) -> Callable[[str, FilterContext], None]:
    def _apply(raw: str, ctx: FilterContext) -> None:
        parts = str(raw).split("-")
        if len(parts) != len(pk_fields):
            return
        for idx, field in enumerate(pk_fields):
            value = parts[idx]
            cast_type = "text"
            if field.endswith("id") or field.endswith("codigo") or field in {"anio", "mes", "mes_num"}:
                cast_type = "int"
            if field == "mes":
                cast_type = "upper_text"
            casted = cast_value(cast_type, value)
            if field == "mes":
                casted = str(casted).upper()
            param_key = f"{field}_{len(ctx.params)}"
            ctx.params[param_key] = casted
            ctx.where.append(f"{quote_identifier(field)} = %({param_key})s")
    return _apply


RESOURCE_CONFIG: dict[str, dict[str, Any]] = {
    "empleados": {
        "select": """
            WITH ult AS (
                SELECT
                    i.empleado_nombre_completo AS nombre,
                    i.trabajo_cargo AS cargo_nombre,
                    i.trabajo_centro_de_costo AS oficina_cc,
                    i.trabajo_fecha_ingreso_compania AS fecha_ingreso,
                    i.periodo,
                    ROW_NUMBER() OVER (
                        PARTITION BY i.empleado_nombre_completo
                        ORDER BY i.periodo DESC NULLS LAST
                    ) AS rn
                FROM talento_cultura.informacion_laboral i
            ),
            buk_estados AS (
                SELECT
                    buk.empleado_nombre_completo,
                    buk.empleado_estado,
                    ROW_NUMBER() OVER (
                        PARTITION BY buk.empleado_nombre_completo
                        ORDER BY buk.periodo DESC NULLS LAST
                    ) AS rn_buk
                FROM talento_cultura.informacion_laboral_buk_staging buk
            )
            SELECT
                t.id::text AS empleado_id,
                u.nombre,
                o.id::text AS oficina_id,
                UPPER(o.nombre) AS oficina_nombre,
                c.id::text AS cargo_id,
                UPPER(COALESCE(c.nombre, u.cargo_nombre)) AS cargo_nombre,
                u.fecha_ingreso,
                COALESCE(b.empleado_estado, 'ACTIVO')::text AS estado_buk
            FROM ult u
            LEFT JOIN public.oficinas o ON o.id = u.oficina_cc
            LEFT JOIN talento_cultura.cat_trabajador t ON LOWER(t.nombre) = LOWER(u.nombre)
            LEFT JOIN talento_cultura.cat_cargo c ON LOWER(c.nombre) = LOWER(u.cargo_nombre)
            LEFT JOIN buk_estados b ON LOWER(b.empleado_nombre_completo) = LOWER(u.nombre) AND b.rn_buk = 1
            WHERE u.rn = 1
        """,
        "order": "oficina_nombre, nombre",
        "table": "talento_cultura.informacion_laboral",
        "pk": ["empleado_id"],
        "accepted_fields": {
            "empleado_id": "text",
            "nombre": "text",
            "oficina_id": "text",
            "oficina_nombre": "text",
            "cargo_id": "text",
            "cargo_nombre": "text",
            "fecha_ingreso": "date",
            "estado_buk": "text",
        },
        "filters": {
            "id": filter_equals("t.id"),
            "oficina_id": filter_equals("o.id"),
            "oficina": filter_contains_tokens_normalized("o.nombre", extra_stopwords={"OFICINA"}),
            "nombre": filter_ilike("u.nombre"),
            "cargo": filter_contains_tokens_normalized("COALESCE(c.nombre, u.cargo_nombre)", extra_stopwords={"OFICINA", "AGENCIA"}),
            "cargo_id": filter_equals("c.id"),
        },
    },
    "ascensos": {
        "select": """
            WITH rango AS (
                SELECT
                    a.periodo,
                    a.oficina_codigo,
                    a.oficina_nombre,
                    a.cantidad,
                    a.observacion,
                    EXTRACT(YEAR FROM a.periodo)::int AS anio,
                    EXTRACT(MONTH FROM a.periodo)::int AS mes_num,
                    upper(to_char(a.periodo, 'TMMonth')) AS mes,
                    make_date(EXTRACT(YEAR FROM a.periodo)::int, EXTRACT(MONTH FROM a.periodo)::int, 1) AS dia_inicio,
                    (make_date(EXTRACT(YEAR FROM a.periodo)::int, EXTRACT(MONTH FROM a.periodo)::int, 1) + INTERVAL '1 month - 1 day')::date AS dia_fin
                FROM talento_cultura.ascensos a
            ),
            buk_activos AS (
                SELECT
                    r.periodo,
                    r.oficina_codigo,
                    COUNT(DISTINCT il.buk_employee_id) AS total_empleados
                FROM rango r
                LEFT JOIN talento_cultura.informacion_laboral_buk_staging il
                  ON (il.trabajo_centro_de_costo)::integer = r.oficina_codigo
                 AND COALESCE(il.trabajo_fecha_ingreso_compania, il.empleado_activo_desde, r.dia_inicio) <= r.dia_fin
                 AND COALESCE(il.trabajo_fecha_termino_trabajo, il.trabajo_fecha_fin_de_contrato, il.empleado_activo_hasta, r.dia_fin) >= r.dia_inicio
                GROUP BY 1, 2
            )
            SELECT
                r.periodo,
                r.oficina_codigo,
                r.oficina_nombre,
                r.cantidad,
                r.observacion,
                r.anio,
                r.mes_num,
                r.mes,
                COALESCE(b.total_empleados, 0) AS total_empleados,
                CASE
                    WHEN COALESCE(b.total_empleados, 0) > 0 THEN ROUND((r.cantidad::numeric * 100) / b.total_empleados, 2)
                    ELSE 0
                END AS variacion_pct
            FROM rango r
            LEFT JOIN buk_activos b
              ON b.periodo = r.periodo
             AND b.oficina_codigo = r.oficina_codigo
        """,
        "order": "periodo DESC, oficina_codigo",
        "table": "talento_cultura.ascensos",
        "pk": ["periodo", "oficina_codigo"],
        "accepted_fields": {
            "periodo": "date",
            "oficina_codigo": "int",
            "cantidad": "int",
            "observacion": "text",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
            "mes_num": filter_period_month("periodo"),
            "oficina_codigo": filter_equals("oficina_codigo", cast="int"),
            "id": parse_ascensos_id,
        },
    },
    "bonos_mensual": {
        "select": """
            SELECT
                anio,
                upper(mes) AS mes,
                cantidad_empleados,
                cantidad_beneficiados,
                valor_bono,
                porcentaje_variacion
            FROM talento_cultura.reporte_bonos_mensual
        """,
        "order": "anio DESC, mes",
        "table": "talento_cultura.reporte_bonos_mensual",
        "pk": ["anio", "mes"],
        "accepted_fields": {
            "anio": "int",
            "mes": "upper_text",
            "cantidad_empleados": "int",
            "cantidad_beneficiados": "int",
            "valor_bono": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("upper(mes)", cast=None, upper=True),
        },
        "id_fields": ["anio", "mes"],
    },
    "bono_cumple": {
        "select": """
            SELECT
                anio,
                upper(mes) AS mes,
                cantidad_empleados,
                cantidad_beneficiados,
                valor_bono,
                total_bono,
                porcentaje_variacion
            FROM talento_cultura.reporte_bono_cumpleanos
        """,
        "order": "anio DESC, mes",
        "table": "talento_cultura.reporte_bono_cumpleanos",
        "pk": ["anio", "mes"],
        "accepted_fields": {
            "anio": "int",
            "mes": "upper_text",
            "cantidad_empleados": "int",
            "cantidad_beneficiados": "int",
            "valor_bono": "numeric",
            "total_bono": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("upper(mes)", upper=True),
        },
        "id_fields": ["anio", "mes"],
    },
    "clima_laboral": {
        "select": """
            SELECT anio, dimension, porcentaje
            FROM talento_cultura.reporte_clima_laboral
        """,
        "order": "anio DESC, dimension",
        "table": "talento_cultura.reporte_clima_laboral",
        "pk": ["anio", "dimension"],
        "accepted_fields": {
            "anio": "int",
            "dimension": "text",
            "porcentaje": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "dimension": filter_ilike("dimension"),
        },
    },
    "desempeno": {
        "select": """
            SELECT anio, oficina, porcentaje
            FROM talento_cultura.reporte_desempeno
        """,
        "order": "anio DESC, oficina",
        "table": "talento_cultura.reporte_desempeno",
        "pk": ["anio", "oficina"],
        "accepted_fields": {
            "anio": "int",
            "oficina": "text",
            "porcentaje": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "oficina": filter_ilike("oficina"),
        },
    },
    "egresos": {
        "select": """
            SELECT
                id,
                anio,
                upper(mes) AS mes,
                oficina_id,
                oficina_nombre,
                cargo_id,
                cargo_nombre,
                cantidad,
                motivo,
                creado_en,
                actualizado_en
            FROM talento_cultura.egresos
        """,
        "order": "anio DESC, mes, oficina_nombre",
        "table": "talento_cultura.egresos",
        "pk": ["id"],
        "accepted_fields": {
            "id": "int",
            "anio": "int",
            "mes": "upper_text",
            "oficina_id": "text",
            "oficina_nombre": "text",
            "cargo_id": "text",
            "cargo_nombre": "text",
            "cantidad": "int",
            "motivo": "text",
        },
        "filters": {
            "id": filter_equals("id", cast="int"),
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("upper(mes)", upper=True),
            "oficina": filter_ilike("oficina_nombre"),
        },
        "input_aliases": {
            "oficina": "oficina_nombre",
            "oficina_codigo": "oficina_id",
            "cargo": "cargo_nombre",
            "cargo_codigo": "cargo_id",
        },
    },
    "rol_lider": {
        "select": """
            SELECT
                periodo,
                EXTRACT(YEAR FROM periodo)::int AS anio,
                EXTRACT(MONTH FROM periodo)::int AS mes_num,
                upper(to_char(periodo, 'TMMonth')) AS mes,
                lider_mujer,
                lider_hombre,
                lider_otro,
                pct_lider_mujer,
                pct_lider_hombre,
                pct_lider_otro
            FROM talento_cultura.liderazgo_genero_input
        """,
        "order": "periodo DESC",
        "table": "talento_cultura.liderazgo_genero_input",
        "pk": ["periodo"],
        "accepted_fields": {
            "periodo": "date",
            "lider_mujer": "int",
            "lider_hombre": "int",
            "lider_otro": "int",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
        },
    },
    "control_disciplinario": {
        "select": """
            SELECT
                id,
                anio,
                trabajador_id,
                trabajador_nombre,
                oficina_id,
                oficina_nombre,
                cargo_id,
                cargo_nombre,
                antiguedad,
                motivo,
                fecha_hechos,
                fecha_conocimiento,
                fecha_notificacion,
                posible_sancion,
                gravedad_notificada,
                fecha_descargos,
                fecha_decision_1,
                gravedad_1,
                sancion_1,
                recurso,
                fecha_interposicion_recurso,
                fecha_decision_recurso,
                decision_recurso,
                gravedad_2,
                sancion_2,
                fecha_decision_2,
                tiempo_suspension,
                etapa_proceso,
                estado_empleado,
                tipo_impacto,
                fecha_creacion,
                fecha_actualizacion,
                inicio_proceso_dias,
                diferencia_dias,
                total_vinculacion_dias,
                duracion_instancia_1,
                duracion_instancia_2
            FROM talento_cultura.control_disciplinario
        """,
        "order": "fecha_creacion DESC",
        "table": "talento_cultura.control_disciplinario",
        "pk": ["id"],
        "accepted_fields": {
            "id": "int",
            "anio": "int",
            "trabajador_id": "text",
            "trabajador_nombre": "text",
            "oficina_id": "text",
            "oficina_nombre": "text",
            "cargo_id": "text",
            "cargo_nombre": "text",
            "antiguedad": "date",
            "motivo": "text",
            "fecha_hechos": "date",
            "fecha_conocimiento": "date",
            "fecha_notificacion": "date",
            "posible_sancion": "text",
            "gravedad_notificada": "text",
            "fecha_descargos": "date",
            "fecha_decision_1": "date",
            "gravedad_1": "text",
            "sancion_1": "text",
            "recurso": "text",
            "fecha_interposicion_recurso": "date",
            "fecha_decision_recurso": "date",
            "decision_recurso": "text",
            "gravedad_2": "text",
            "sancion_2": "text",
            "fecha_decision_2": "date",
            "tiempo_suspension": "text",
            "etapa_proceso": "text",
            "estado_empleado": "text",
            "tipo_impacto": "text",
        },
        "filters": {
            "id": filter_equals("id", cast="int"),
            "anio": filter_equals("anio", cast="int"),
            "estado_empleado": filter_equals("upper(estado_empleado)", upper=True),
            "oficina_id": filter_equals("oficina_id"),
            "trabajador_id": filter_equals("trabajador_id"),
        },
    },
    "capacitacion_mensual": {
        "select": """
            SELECT
                id,
                periodo,
                EXTRACT(YEAR FROM periodo)::int AS anio,
                EXTRACT(MONTH FROM periodo)::int AS mes_num,
                upper(to_char(periodo, 'TMMonth')) AS mes,
                total_gastos,
                trabajadores_cap,
                modalidad,
                rentabilidad,
                grupo,
                costo_por_trabajador
            FROM talento_cultura.capacitacion_mensual
        """,
        "order": "periodo DESC, grupo",
        "table": "talento_cultura.capacitacion_mensual",
        "pk": ["id"],
        "accepted_fields": {
            "id": "int",
            "periodo": "date",
            "total_gastos": "numeric",
            "trabajadores_cap": "int",
            "modalidad": "upper_text",
            "rentabilidad": "upper_text",
            "grupo": "int",
            "costo_por_trabajador": "numeric",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "id": filter_equals("id", cast="int"),
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
            "modalidad": filter_equals("upper(modalidad)", upper=True),
            "grupo": filter_equals("grupo", cast="int"),
        },
        "input_aliases": {
            "TotalGastosTransferencia": "total_gastos",
            "totalGastosTransferencia": "total_gastos",
            "total_gastos_transferencia": "total_gastos",
            "TrabajadoresCapacitados": "trabajadores_cap",
            "trabajadoresCapacitados": "trabajadores_cap",
            "CostoPorTrabajador": "costo_por_trabajador",
            "costoPorTrabajador": "costo_por_trabajador",
        },
    },
    "formacion_participacion": {
        "select": """
            SELECT
                periodo,
                EXTRACT(YEAR FROM periodo)::int AS anio,
                EXTRACT(MONTH FROM periodo)::int AS mes_num,
                upper(to_char(periodo, 'TMMonth')) AS mes,
                oficina_dependencia,
                rol,
                tema_formacion,
                tipo_formacion,
                cant_trab_participaron,
                total_participantes,
                veces_formado,
                calificacion,
                grupo,
                total_participantes_text,
                pct_participacion
            FROM talento_cultura.formacion_participacion
        """,
        "order": "periodo DESC, oficina_dependencia, rol",
        "table": "talento_cultura.formacion_participacion",
        "pk": [
            "periodo",
            "oficina_dependencia",
            "rol",
            "tema_formacion",
            "tipo_formacion",
            "grupo",
        ],
        "accepted_fields": {
            "periodo": "date",
            "oficina_dependencia": "text",
            "rol": "text",
            "tema_formacion": "text",
            "tipo_formacion": "text",
            "cant_trab_participaron": "int",
            "total_participantes": "int",
            "veces_formado": "int",
            "calificacion": "numeric",
            "grupo": "int",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
            "oficina": filter_ilike("oficina_dependencia"),
            "rol": filter_ilike("rol"),
            "tema": filter_ilike("tema_formacion"),
        },
        "input_aliases": {
            "Oficina": "oficina_dependencia",
            "oficina": "oficina_dependencia",
            "Roles": "rol",
            "roles": "rol",
            "TemaFormacion": "tema_formacion",
            "temaFormacion": "tema_formacion",
            "TipoFormacion": "tipo_formacion",
            "tipoFormacion": "tipo_formacion",
            "CantidadTrabajadores": "cant_trab_participaron",
            "cantidadTrabajadores": "cant_trab_participaron",
            "TotalParticipantes": "total_participantes",
            "totalParticipantes": "total_participantes",
            "NumeroVecesFormado": "veces_formado",
            "numeroVecesFormado": "veces_formado",
            "Calificacion": "calificacion",
            "Grupo": "grupo",
        },
    },
    "satisfaccion_aprendizaje": {
        "select": """
            SELECT
                periodo,
                EXTRACT(YEAR FROM periodo)::int AS anio,
                EXTRACT(MONTH FROM periodo)::int AS mes_num,
                upper(to_char(periodo, 'TMMonth')) AS mes,
                n_formadores_recomendacion,
                total_formadores,
                pct_satisfaccion,
                formadores_o_area,
                recomendacion
            FROM talento_cultura.satisfaccion_aprendizaje
        """,
        "order": "periodo DESC, formadores_o_area",
        "table": "talento_cultura.satisfaccion_aprendizaje",
        "pk": ["periodo", "formadores_o_area"],
        "accepted_fields": {
            "periodo": "date",
            "n_formadores_recomendacion": "int",
            "total_formadores": "int",
            "pct_satisfaccion": "numeric",
            "formadores_o_area": "text",
            "recomendacion": "text",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
            "formadores_o_area": filter_ilike("formadores_o_area"),
        },
        "input_aliases": {
            "NumeroFormadoresConRecomendacion": "n_formadores_recomendacion",
            "numeroFormadoresConRecomendacion": "n_formadores_recomendacion",
            "TotalFormadores": "total_formadores",
            "totalFormadores": "total_formadores",
            "PorcentajeSatisfaccion": "pct_satisfaccion",
            "porcentajeSatisfaccion": "pct_satisfaccion",
            "Formadores": "formadores_o_area",
            "formadores": "formadores_o_area",
            "Recomendaciones": "recomendacion",
            "recomendaciones": "recomendacion",
        },
    },
    "transferencia_conocimiento": {
        "select": """
            SELECT
                periodo,
                EXTRACT(YEAR FROM periodo)::int AS anio,
                EXTRACT(MONTH FROM periodo)::int AS mes_num,
                upper(to_char(periodo, 'TMMonth')) AS mes,
                comprension,
                retencion,
                valoracion_desempeno,
                satisfaccion,
                valoracion_jefe_inmediato,
                practica,
                total,
                efectividad
            FROM talento_cultura.transferencia_conocimiento
        """,
        "order": "periodo DESC",
        "table": "talento_cultura.transferencia_conocimiento",
        "pk": ["periodo"],
        "accepted_fields": {
            "periodo": "date",
            "comprension": "numeric",
            "retencion": "numeric",
            "valoracion_desempeno": "numeric",
            "satisfaccion": "numeric",
            "valoracion_jefe_inmediato": "numeric",
            "practica": "numeric",
            "total": "numeric",
            "efectividad": "numeric",
        },
        "period_field": "periodo",
        "period_keys": ("anio", "mes"),
        "filters": {
            "anio": filter_period_year("periodo"),
            "mes": filter_period_month("periodo"),
        },
        "input_aliases": {
            "liderMujer": "lider_mujer",
            "liderHombre": "lider_hombre",
            "liderOtro": "lider_otro",
        },
    },
    "accidentalidad": {
        "select": """
            SELECT
                a.id,
                a.anio,
                upper(a.mes) AS mes,
                a.tipo_vinculacion,
                a.numero_accidentes,
                a.accidentes_mortales,
                a.dias_cargados,
                a.indicador,
                a.resultado,
                (
                  WITH empleados_unicos AS (
                    SELECT DISTINCT ON (il.empleado_nombre_completo)
                      il.empleado_nombre_completo,
                      il.trabajo_fecha_ingreso_compania,
                      il.trabajo_fecha_termino_trabajo
                    FROM talento_cultura.informacion_laboral_buk_staging il
                    WHERE (
                        -- Empleado activo en el mes específico
                        (il.trabajo_fecha_ingreso_compania IS NULL OR il.trabajo_fecha_ingreso_compania <= (make_date(a.anio, 
                          CASE 
                            WHEN upper(a.mes) = 'ENERO' THEN 1
                            WHEN upper(a.mes) = 'FEBRERO' THEN 2
                            WHEN upper(a.mes) = 'MARZO' THEN 3
                            WHEN upper(a.mes) = 'ABRIL' THEN 4
                            WHEN upper(a.mes) = 'MAYO' THEN 5
                            WHEN upper(a.mes) = 'JUNIO' THEN 6
                            WHEN upper(a.mes) = 'JULIO' THEN 7
                            WHEN upper(a.mes) = 'AGOSTO' THEN 8
                            WHEN upper(a.mes) = 'SEPTIEMBRE' THEN 9
                            WHEN upper(a.mes) = 'OCTUBRE' THEN 10
                            WHEN upper(a.mes) = 'NOVIEMBRE' THEN 11
                            WHEN upper(a.mes) = 'DICIEMBRE' THEN 12
                            ELSE 1
                          END, 1) + interval '1 month - 1 day')::date)
                        AND (il.trabajo_fecha_termino_trabajo IS NULL OR il.trabajo_fecha_termino_trabajo >= make_date(a.anio, 
                          CASE 
                            WHEN upper(a.mes) = 'ENERO' THEN 1
                            WHEN upper(a.mes) = 'FEBRERO' THEN 2
                            WHEN upper(a.mes) = 'MARZO' THEN 3
                            WHEN upper(a.mes) = 'ABRIL' THEN 4
                            WHEN upper(a.mes) = 'MAYO' THEN 5
                            WHEN upper(a.mes) = 'JUNIO' THEN 6
                            WHEN upper(a.mes) = 'JULIO' THEN 7
                            WHEN upper(a.mes) = 'AGOSTO' THEN 8
                            WHEN upper(a.mes) = 'SEPTIEMBRE' THEN 9
                            WHEN upper(a.mes) = 'OCTUBRE' THEN 10
                            WHEN upper(a.mes) = 'NOVIEMBRE' THEN 11
                            WHEN upper(a.mes) = 'DICIEMBRE' THEN 12
                            ELSE 1
                          END, 1))
                      )
                    ORDER BY il.empleado_nombre_completo, 
                             CASE WHEN il.trabajo_fecha_termino_trabajo IS NULL THEN 1 ELSE 0 END DESC,
                             il.trabajo_fecha_termino_trabajo DESC
                  )
                  SELECT COUNT(*)
                  FROM empleados_unicos eu
                  WHERE (
                    -- Propios: sin fecha de término O contrato > 1 año
                    (eu.trabajo_fecha_termino_trabajo IS NULL) 
                    OR 
                    (eu.trabajo_fecha_termino_trabajo IS NOT NULL 
                     AND eu.trabajo_fecha_ingreso_compania IS NOT NULL
                     AND eu.trabajo_fecha_termino_trabajo > (eu.trabajo_fecha_ingreso_compania + INTERVAL '1 year'))
                  )
                ) AS numero_trabajadores_propios,
                (
                  WITH empleados_unicos AS (
                    SELECT DISTINCT ON (il.empleado_nombre_completo)
                      il.empleado_nombre_completo,
                      il.trabajo_fecha_ingreso_compania,
                      il.trabajo_fecha_termino_trabajo
                    FROM talento_cultura.informacion_laboral_buk_staging il
                    WHERE (
                        -- Empleado activo en el mes específico
                        (il.trabajo_fecha_ingreso_compania IS NULL OR il.trabajo_fecha_ingreso_compania <= (make_date(a.anio, 
                          CASE 
                            WHEN upper(a.mes) = 'ENERO' THEN 1
                            WHEN upper(a.mes) = 'FEBRERO' THEN 2
                            WHEN upper(a.mes) = 'MARZO' THEN 3
                            WHEN upper(a.mes) = 'ABRIL' THEN 4
                            WHEN upper(a.mes) = 'MAYO' THEN 5
                            WHEN upper(a.mes) = 'JUNIO' THEN 6
                            WHEN upper(a.mes) = 'JULIO' THEN 7
                            WHEN upper(a.mes) = 'AGOSTO' THEN 8
                            WHEN upper(a.mes) = 'SEPTIEMBRE' THEN 9
                            WHEN upper(a.mes) = 'OCTUBRE' THEN 10
                            WHEN upper(a.mes) = 'NOVIEMBRE' THEN 11
                            WHEN upper(a.mes) = 'DICIEMBRE' THEN 12
                            ELSE 1
                          END, 1) + interval '1 month - 1 day')::date)
                        AND (il.trabajo_fecha_termino_trabajo IS NULL OR il.trabajo_fecha_termino_trabajo >= make_date(a.anio, 
                          CASE 
                            WHEN upper(a.mes) = 'ENERO' THEN 1
                            WHEN upper(a.mes) = 'FEBRERO' THEN 2
                            WHEN upper(a.mes) = 'MARZO' THEN 3
                            WHEN upper(a.mes) = 'ABRIL' THEN 4
                            WHEN upper(a.mes) = 'MAYO' THEN 5
                            WHEN upper(a.mes) = 'JUNIO' THEN 6
                            WHEN upper(a.mes) = 'JULIO' THEN 7
                            WHEN upper(a.mes) = 'AGOSTO' THEN 8
                            WHEN upper(a.mes) = 'SEPTIEMBRE' THEN 9
                            WHEN upper(a.mes) = 'OCTUBRE' THEN 10
                            WHEN upper(a.mes) = 'NOVIEMBRE' THEN 11
                            WHEN upper(a.mes) = 'DICIEMBRE' THEN 12
                            ELSE 1
                          END, 1))
                      )
                    ORDER BY il.empleado_nombre_completo, 
                             CASE WHEN il.trabajo_fecha_termino_trabajo IS NULL THEN 1 ELSE 0 END DESC,
                             il.trabajo_fecha_termino_trabajo DESC
                  )
                  SELECT COUNT(*)
                  FROM empleados_unicos eu
                  WHERE (
                    -- Contratistas: contrato ≤ 1 año
                    eu.trabajo_fecha_termino_trabajo IS NOT NULL
                    AND eu.trabajo_fecha_ingreso_compania IS NOT NULL
                    AND eu.trabajo_fecha_termino_trabajo <= (eu.trabajo_fecha_ingreso_compania + INTERVAL '1 year')
                  )
                ) AS numero_trabajadores_contratistas,
                a.numero_trabajadores,
                a.dias_incapacidad,
                a.creado_en,
                a.actualizado_en
            FROM talento_cultura.accidentalidad a
        """,
        "order": "anio DESC, mes, tipo_vinculacion",
        "table": "talento_cultura.accidentalidad",
        "pk": ["id"],
        "accepted_fields": {
            "id": "int",
            "anio": "int",
            "mes": "upper_text",
            "tipo_vinculacion": "text",
            "numero_accidentes": "int",
            "accidentes_mortales": "int",
            "dias_cargados": "int",
            "indicador": "text",
            "resultado": "numeric",
            "numero_trabajadores": "int",
            "numero_trabajadores_propios": "int",
            "numero_trabajadores_contratistas": "int",
            "dias_incapacidad": "int",
        },
        "filters": {
            "id": filter_equals("id", cast="int"),
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("upper(mes)", upper=True),
            "tipo_vinculacion": filter_equals("upper(tipo_vinculacion)", upper=True),
        },
        "input_aliases": {
            "accidentes": "numero_accidentes",
            "accidentes_trabajo": "numero_accidentes",
            "accidentesTrabajo": "numero_accidentes",
            "accidentes_mortales": "accidentes_mortales",
            "at_mortales": "accidentes_mortales",
            "AtMortales": "accidentes_mortales",
            "dias_cargados": "dias_cargados",
            "dias_incapacidad": "dias_incapacidad",
            "numero_trabajadores": "numero_trabajadores",
            "numero_trabajadores_propios": "numero_trabajadores_propios",
            "numero_trabajadores_contratistas": "numero_trabajadores_contratistas",
        },
    },
    "ausentismo": {
        "select": """
            SELECT
                a.anio,
                a.mes,
                a."DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL PROP" AS dias_propios,
                a."DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL CONT" AS dias_contratistas,
                a."NÚMERO DE DIAS LABORALES EN EL MES" AS dias_laborales,
                a.total_dias_incapacidad,
                a.numero_dias_programados,
                a.ausentismo_laboral,
                (
                  SELECT COUNT(*)
                  FROM talento_cultura.informacion_laboral_buk_staging il
                  WHERE (il.trabajo_fecha_ingreso_compania IS NULL OR il.trabajo_fecha_ingreso_compania <= (make_date(a.anio, a.mes, 1) + interval '1 month - 1 day')::date)
                    AND (il.trabajo_fecha_termino_trabajo IS NULL OR il.trabajo_fecha_termino_trabajo >= make_date(a.anio, a.mes, 1))
                ) AS numero_trabajadores
            FROM talento_cultura.parametros_ausentismo a
        """,
        "order": "anio DESC, mes DESC",
        "table": "talento_cultura.parametros_ausentismo",
        "pk": ["anio", "mes"],
        "accepted_fields": {
            "anio": "int",
            "mes": "int",
            "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL PROP": "int",
            "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL CONT": "int",
            "NÚMERO DE DIAS LABORALES EN EL MES": "int",
            "total_dias_incapacidad": "int",
            "numero_dias_programados": "int",
            "ausentismo_laboral": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("mes", cast="int"),
        },
        "input_aliases": {
            "dias_propios": "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL PROP",
            "dias_ausencia_propios": "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL PROP",
            "dias_contratistas": "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL CONT",
            "dias_ausencia_contratistas": "DIAS DE AUSENCIA POR INCAPACIDAD LABORAL Y COMÚN PERSONAL CONT",
            "dias_laborales": "NÚMERO DE DIAS LABORALES EN EL MES",
            "dias_laborales_mes": "NÚMERO DE DIAS LABORALES EN EL MES",
            "total_dias_incapacidad": "total_dias_incapacidad",
            "dias_trabajo_programados": "numero_dias_programados",
            "numero_dias_programados": "numero_dias_programados",
            "ausentismo": "ausentismo_laboral",
            "ausentismo_laboral": "ausentismo_laboral",
        },
    },
    "enfermedad_laboral": {
        "select": """
            SELECT
                e.id,
                e.anio,
                e.mes,
                e."Casos antiguos de EL" AS casos_antiguos,
                e."Casos Nuevos de EL" AS casos_nuevos,
                e."Constante" AS constante,
                e.indicador,
                e.resultado,
                e."CODIGO CIE-10" AS codigo_cie10,
                e."Clasificación Internacional de Enfermedades" AS clasificacion_internacional,
                e."CLASIFICACION ENFERMEDAD LABORAL" AS clasificacion_enfermedad,
                (
                  SELECT COUNT(DISTINCT il.empleado_nombre_completo)
                  FROM talento_cultura.informacion_laboral_buk_staging il
                  WHERE (il.trabajo_fecha_ingreso_compania IS NULL OR il.trabajo_fecha_ingreso_compania <= (make_date(e.anio, e.mes, 1) + interval '1 month - 1 day')::date)
                    AND (il.trabajo_fecha_termino_trabajo IS NULL OR il.trabajo_fecha_termino_trabajo >= make_date(e.anio, e.mes, 1))
                ) AS numero_trabajadores_anio
            FROM talento_cultura.parametros_enfermedad_laboral e
        """,
        "order": "anio DESC, mes DESC, indicador",
        "table": "talento_cultura.parametros_enfermedad_laboral",
        "pk": ["id"],
        "accepted_fields": {
            "id": "int",
            "anio": "int",
            "mes": "int",
            "Casos antiguos de EL": "int",
            "Casos Nuevos de EL": "int",
            "Constante": "numeric",
            "indicador": "upper_text",
            "resultado": "numeric",
            "CODIGO CIE-10": "text",
            "Clasificación Internacional de Enfermedades": "text",
            "CLASIFICACION ENFERMEDAD LABORAL": "text",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("mes", cast="int"),
            "indicador": filter_equals("upper(indicador)", upper=True),
        },
        "input_aliases": {
            "casos_antiguos": "Casos antiguos de EL",
            "casos_nuevos": "Casos Nuevos de EL",
            "codigo_cie10": "CODIGO CIE-10",
            "clasificacion_internacional": "Clasificación Internacional de Enfermedades",
            "clasificacion_cie": "Clasificación Internacional de Enfermedades",
            "clasificacion_enfermedad": "CLASIFICACION ENFERMEDAD LABORAL",
            "constante": "Constante",
        },
    },
    "plan_trabajo": {
        "select": """
            SELECT
                anio,
                mes,
                ciclo,
                actividad,
                planeado,
                ejecutado,
                responsable,
                recurso_administrativo,
                recurso_financiero,
                total_actividades,
                actividades_programadas_mes,
                porcentaje_ejecucion_mensual,
                porcentaje_cumplimiento_meta,
                created_at,
                updated_at
            FROM talento_cultura.plan_trabajo_anual
        """,
        "order": "anio DESC, mes DESC, ciclo, actividad",
        "table": "talento_cultura.plan_trabajo_anual",
        "pk": ["anio", "mes", "ciclo", "actividad"],
        "accepted_fields": {
            "anio": "int",
            "mes": "int",
            "ciclo": "text",
            "actividad": "text",
            "planeado": "int",
            "ejecutado": "int",
            "responsable": "text",
            "recurso_administrativo": "bool",
            "recurso_financiero": "bool",
            "total_actividades": "int",
            "actividades_programadas_mes": "int",
            "porcentaje_ejecucion_mensual": "numeric",
            "porcentaje_cumplimiento_meta": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("mes", cast="int"),
            "ciclo": filter_ilike("ciclo"),
        },
    },
    "programa_capacitaciones": {
        "select": """
            SELECT
                anio,
                mes,
                actividad,
                planeado,
                ejecutado,
                responsable,
                recurso_administrativo,
                recurso_financiero,
                observaciones,
                total_actividades,
                actividades_programadas_mes,
                porcentaje_ejecucion_mensual,
                porcentaje_cumplimiento_meta,
                created_at,
                updated_at
            FROM talento_cultura.programa_capacitaciones
        """,
        "order": "anio DESC, mes DESC, actividad",
        "table": "talento_cultura.programa_capacitaciones",
        "pk": ["anio", "mes", "actividad"],
        "accepted_fields": {
            "anio": "int",
            "mes": "int",
            "actividad": "text",
            "planeado": "int",
            "ejecutado": "int",
            "responsable": "text",
            "recurso_administrativo": "bool",
            "recurso_financiero": "bool",
            "observaciones": "text",
            "total_actividades": "int",
            "actividades_programadas_mes": "int",
            "porcentaje_ejecucion_mensual": "numeric",
            "porcentaje_cumplimiento_meta": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "mes": filter_equals("mes", cast="int"),
            "actividad": filter_ilike("actividad"),
        },
    },
    "reporte_ministerio": {
        "select": """
            SELECT
                anio,
                recursos,
                gestion_integral,
                gestion_salud,
                gestion_peligros,
                gestion_amenazas,
                verificacion_sgsst,
                mejoramiento,
                porcentaje,
                creado_en,
                actualizado_en
            FROM talento_cultura.reporte_ministerio
        """,
        "order": "anio DESC",
        "table": "talento_cultura.reporte_ministerio",
        "pk": ["anio"],
        "accepted_fields": {
            "anio": "int",
            "recursos": "numeric",
            "gestion_integral": "numeric",
            "gestion_salud": "numeric",
            "gestion_peligros": "numeric",
            "gestion_amenazas": "numeric",
            "verificacion_sgsst": "numeric",
            "mejoramiento": "numeric",
            "porcentaje": "numeric",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
        },
    },
    "restricciones_laborales": {
        "select": """
            SELECT
                anio,
                sede,
                cargo,
                patologia,
                restricciones,
                creado_en,
                actualizado_en
            FROM talento_cultura.restricciones_laborales
        """,
        "order": "anio DESC, sede, cargo",
        "table": "talento_cultura.restricciones_laborales",
        "pk": ["anio", "sede", "cargo", "patologia"],
        "accepted_fields": {
            "anio": "int",
            "sede": "text",
            "cargo": "text",
            "patologia": "text",
            "restricciones": "text",
        },
        "filters": {
            "anio": filter_equals("anio", cast="int"),
            "sede": filter_ilike("sede"),
            "cargo": filter_ilike("cargo"),
            "patologia": filter_ilike("patologia"),
        },
    },
}


def fetch_dicts(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_filters(resource: dict[str, Any], query_params) -> FilterContext:
    filters_conf: dict[str, Callable[[str, FilterContext], None]] = resource.get("filters", {})
    ctx = FilterContext(where=[], params={})
    for key, fn in filters_conf.items():
        if key in query_params and query_params.get(key) not in (None, ""):
            fn(query_params.get(key), ctx)
    return ctx


def apply_period_fields(resource: dict[str, Any], data: dict[str, Any]) -> None:
    period_field = resource.get("period_field")
    if not period_field:
        return
    if period_field in data and data[period_field] not in (None, ""):
        data[period_field] = cast_value("date", data[period_field])
        return
    keys = resource.get("period_keys", ("anio", "mes"))
    anio_key, mes_key = keys
    if anio_key in data and mes_key in data:
        periodo = build_periodo(data[anio_key], data[mes_key])
        data[period_field] = periodo
        # En la mayoría de casos no almacenamos anio/mes directamente en la tabla
        if anio_key not in resource["accepted_fields"]:
            data.pop(anio_key, None)
        if mes_key not in resource["accepted_fields"]:
            data.pop(mes_key, None)


def prepare_payload(resource: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if hasattr(incoming, "items"):
        for key, value in incoming.items():
            data[key] = value
    else:
        data.update(incoming)
    aliases = resource.get("input_aliases", {})
    for alias, target in aliases.items():
        if alias in data and target not in data:
            data[target] = data[alias]
    accepted_fields = resource.get("accepted_fields", {})
    normalized_map = {normalize_key(field): field for field in accepted_fields.keys()}
    for key, value in list(data.items()):
        if key in accepted_fields:
            continue
        normalized = normalize_key(key)
        target_field = normalized_map.get(normalized)
        if target_field and target_field not in data:
            data[target_field] = value
    apply_period_fields(resource, data)
    accepted: dict[str, Any] = {}
    for field, field_type in accepted_fields.items():
        if field in data:
            accepted[field] = cast_value(field_type, data[field])
    return {k: v for k, v in accepted.items() if k in accepted_fields}


def extract_pk(resource: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    pk_values: dict[str, Any] = {}
    for field in resource.get("pk", []):
        if field not in payload or payload[field] in (None, ""):
            raise ValueError(f"Falta el campo clave '{field}'")
        pk_values[field] = payload[field]
    return pk_values


def split_update_data(resource: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pk_values = extract_pk(resource, payload)
    data = {k: v for k, v in payload.items() if k not in pk_values}
    if not data:
        raise ValueError("No se enviaron campos para actualizar")
    return pk_values, data


def build_where_from_pk(pk_values: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    where_clauses = []
    params = {}
    for idx, (field, value) in enumerate(pk_values.items()):
        param_key = f"pk_{idx}"
        where_clauses.append(f"{quote_identifier(field)} = %({param_key})s")
        params[param_key] = value
    return " AND ".join(where_clauses), params


def combine_request_data(request, include_query: bool = False) -> dict[str, Any]:
    combined: dict[str, Any] = {}
    if include_query and hasattr(request, "query_params"):
        for key, value in request.query_params.items():
            combined.setdefault(key, value)
    if hasattr(request.data, "items"):
        for key, value in request.data.items():
            combined[key] = value
    else:
        combined.update(getattr(request, "data", {}) or {})
    return combined


def _year_from_first_date(values: list[Any]) -> int | None:
    for v in values:
        if v not in (None, ""):
            try:
                d = parse_date_value(v)
                return d.year
            except Exception:
                continue
    return None


def _lookup_catalog_id(table: str, nombre: str) -> str | None:
    if not nombre:
        return None
    safe_table = quote_identifier(table)
    sql = f"SELECT id FROM talento_cultura.{safe_table} WHERE nombre ILIKE %(n)s LIMIT 1"
    with connections['default'].cursor() as cursor:
        cursor.execute(sql, {"n": nombre})
        row = cursor.fetchone()
        if row:
            return str(row[0])
    return None


def enrich_control_disciplinario_payload(payload: dict[str, Any]) -> dict[str, Any]:
    # Asegurar anio si viene ausente, derivándolo de alguna fecha relevante
    if payload.get("anio") in (None, ""):
        maybe_year = _year_from_first_date([
            payload.get("fecha_notificacion"),
            payload.get("fecha_hechos"),
            payload.get("fecha_conocimiento"),
        ])
        if maybe_year is not None:
            payload["anio"] = maybe_year

    # Resolver IDs de catálogos a partir del nombre cuando falten
    if payload.get("trabajador_id") in (None, "") and payload.get("trabajador_nombre"):
        nombre = str(payload.get("trabajador_nombre"))
        found = _lookup_catalog_id("cat_trabajador", nombre)
        if not found:
            # Intento alterno: empleados_dim
            with connections['default'].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT empleado_id
                    FROM talento_cultura.empleados_dim
                    WHERE nombre ILIKE %(n)s
                    LIMIT 1
                    """,
                    {"n": nombre},
                )
                row = cursor.fetchone()
                if row:
                    found = str(row[0])
        if found:
            payload["trabajador_id"] = found
        else:
            # Último recurso: usar el nombre como identificador textual para cumplir NOT NULL
            payload["trabajador_id"] = nombre
    if payload.get("oficina_id") in (None, "") and payload.get("oficina_nombre"):
        found = _lookup_catalog_id("cat_oficina", str(payload.get("oficina_nombre")))
        if found:
            payload["oficina_id"] = found
    if payload.get("cargo_id") in (None, "") and payload.get("cargo_nombre"):
        found = _lookup_catalog_id("cat_cargo", str(payload.get("cargo_nombre")))
        if found:
            payload["cargo_id"] = found

    return payload


class TalentoResourceView(APIView):
    permission_classes = [IsAuthenticated]
    resource_name: str = ""

    def get_resource(self) -> dict[str, Any]:
        if self.resource_name not in RESOURCE_CONFIG:
            raise ValueError("Recurso no configurado")
        return RESOURCE_CONFIG[self.resource_name]

    def get(self, request, *args, **kwargs):
        resource = self.get_resource()
        ctx = build_filters(resource, request.query_params)
        sql = resource["select"]
        if ctx.where:
            base = sql.lower()
            conj = " AND ".join(ctx.where)
            if " where " in base:
                sql = f"{sql}\n AND {conj}"
            else:
                sql = f"{sql}\n WHERE {conj}"
        if resource.get("order"):
            sql = f"{sql}\n ORDER BY {resource['order']}"
        with connections['default'].cursor() as cursor:
            cursor.execute(sql, ctx.params)
            rows = fetch_dicts(cursor)
        return Response({"items": rows})

    def post(self, request, *args, **kwargs):
        resource = self.get_resource()
        payload = prepare_payload(resource, combine_request_data(request, include_query=True))
        # Regla de unicidad lógica para enfermedad_laboral: (anio, mes, indicador, CIE-10)
        if getattr(self, "resource_name", None) == "enfermedad_laboral":
            anio = payload.get("anio")
            mes = payload.get("mes")
            indicador = payload.get("indicador")
            cie = payload.get("CODIGO CIE-10")
            if anio is not None and mes is not None and indicador not in (None, ""):
                sql_dup = (
                    "SELECT 1 FROM talento_cultura.parametros_enfermedad_laboral "
                    "WHERE anio=%(anio)s AND mes=%(mes)s "
                    "AND upper(indicador)=upper(%(ind)s) "
                    "AND COALESCE(\"CODIGO CIE-10\", '') = COALESCE(%(cie)s, '') "
                    "LIMIT 1"
                )
                with connections['default'].cursor() as cursor:
                    cursor.execute(sql_dup, {"anio": anio, "mes": mes, "ind": indicador, "cie": cie})
                    if cursor.fetchone():
                        return Response({"detail": "Registro duplicado (anio, mes, indicador, CIE-10)"}, status=status.HTTP_409_CONFLICT)
        # Fallback específico: en control_disciplinario, si no viene 'anio',
        # derivarlo de alguna fecha o usar el año actual
        if getattr(self, "resource_name", None) == "control_disciplinario":
            if payload.get("anio") in (None, ""):
                for key in ("fecha_notificacion", "fecha_hechos", "fecha_conocimiento"):
                    v = payload.get(key)
                    if v:
                        try:
                            d = v if isinstance(v, date) else parse_date_value(v)
                            payload["anio"] = d.year
                            break
                        except Exception:
                            pass
                if payload.get("anio") in (None, ""):
                    payload["anio"] = date.today().year
        if not payload:
            return Response({"detail": "No se enviaron datos válidos"}, status=status.HTTP_400_BAD_REQUEST)
        # Enriquecimiento específico de recurso (control disciplinario):
        if self.resource_name == "control_disciplinario":
            payload = enrich_control_disciplinario_payload(payload)
            # Validación de campos mínimos conocidos por la tabla
            missing: list[str] = []
            for req in ("anio", "trabajador_nombre"):
                if payload.get(req) in (None, ""):
                    missing.append(req)
            # trabajador_id es NOT NULL en BD; intentamos mapearlo arriba, pero si no se puede,
            # dejamos que la BD falle con un error de integridad para reflejar el problema de datos.
            if missing:
                return Response({"detail": f"Faltan campos requeridos: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        columns = ", ".join(quote_identifier(col) for col in payload.keys())
        placeholders = ", ".join([f"%({key})s" for key in payload.keys()])
        pk_fields = resource.get("pk", [])
        returning_clause = ""
        if pk_fields:
            returning_clause = " RETURNING " + ", ".join(quote_identifier(col) for col in pk_fields)
        pk_values: dict[str, Any] = {}
        try:
            with transaction.atomic():
                with connections['default'].cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO {resource['table']} ({columns}) VALUES ({placeholders}){returning_clause}",
                        payload,
                    )
                    if returning_clause:
                        returned = cursor.fetchone()
                        if returned is not None:
                            returned_cols = [col[0] for col in cursor.description]
                            pk_values = dict(zip(returned_cols, returned))
        except IntegrityError as exc:
            # Errores típicos: PK duplicada, NOT NULL, FK, etc.
            msg = str(exc)
            status_code = status.HTTP_409_CONFLICT if 'duplicate key value' in msg.lower() else status.HTTP_400_BAD_REQUEST
            return Response({"detail": msg}, status=status_code)
        if not pk_values and pk_fields:
            pk_values = {field: payload[field] for field in pk_fields if field in payload}

        select_sql = resource["select"]
        params: dict[str, Any] = {}
        if pk_values:
            where_clause, params = build_where_from_pk(pk_values)
            select_sql = f"{select_sql}\n WHERE {where_clause}"
        elif resource.get("order"):
            select_sql = f"{select_sql}\n ORDER BY {resource['order']}"
        with connections['default'].cursor() as cursor:
            cursor.execute(select_sql, params)
            rows = fetch_dicts(cursor)
        return Response({"items": rows}, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        resource = self.get_resource()
        incoming = combine_request_data(request, include_query=True)
        # Permitir cambiar valores de PK: soportamos claves 'where_<pk>' o 'old_<pk>'
        # y, si el recurso define 'period_field', aceptar 'where_anio' + 'where_mes'.
        where_override: dict[str, Any] = {}
        pk_fields: list[str] = resource.get("pk", [])
        period_field: str | None = resource.get("period_field")
        period_keys = resource.get("period_keys", ("anio", "mes"))
        accepted_types = resource.get("accepted_fields", {})
        # Build where overrides for direct PKs
        for field in pk_fields:
            for prefix in ("where_", "old_"):
                key = prefix + field
                if key in incoming and incoming[key] not in (None, ""):
                    ftype = accepted_types.get(field, "text")
                    where_override[field] = cast_value(ftype, incoming[key])
                    break
        # Support period anio/mes overrides
        if period_field and (f"where_{period_keys[0]}" in incoming or f"where_{period_keys[1]}" in incoming):
            try:
                anio_raw = incoming.get(f"where_{period_keys[0]}")
                mes_raw = incoming.get(f"where_{period_keys[1]}")
                if anio_raw not in (None, "") and mes_raw not in (None, ""):
                    periodo = build_periodo(anio_raw, mes_raw)
                    where_override[period_field] = periodo
            except Exception:
                pass
        payload = prepare_payload(resource, incoming)
        if not payload:
            return Response({"detail": "No se enviaron datos válidos"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pk_values, data = split_update_data(resource, payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        # Preparar WHERE primero (usando overrides si existen)
        ci_fields = set(resource.get("pk_case_insensitive", []))
        base_where = {**pk_values}
        base_where.update(where_override)
        where_parts: list[str] = []
        where_params: dict[str, Any] = {}
        for idx, (field, value) in enumerate(base_where.items()):
            param_key = f"pk_{idx}"
            where_params[param_key] = value
            col = quote_identifier(field)
            if field in ci_fields:
                where_parts.append(f"upper({col}) = upper(%({param_key})s)")
            else:
                where_parts.append(f"{col} = %({param_key})s")
        where_clause = " AND ".join(where_parts)

        # Si el recurso usa period_field y llegó solo 'mes' (sin 'periodo'),
        # construimos el nuevo periodo con el año actual del registro.
        period_field = resource.get("period_field")
        period_keys = resource.get("period_keys", ("anio", "mes"))
        if period_field and (period_field not in data):
            mes_key = period_keys[1]
            if mes_key in incoming and incoming.get(mes_key) not in (None, ""):
                try:
                    # Preferir 'anio' entrante; si no, tomar año actual del registro
                    if period_keys[0] in incoming and incoming.get(period_keys[0]) not in (None, ""):
                        base_year = int(incoming.get(period_keys[0]))
                    else:
                        sql_year = f"SELECT EXTRACT(YEAR FROM {period_field})::int FROM {resource['table']} WHERE {where_clause} LIMIT 1"
                        with connections['default'].cursor() as cursor:
                            cursor.execute(sql_year, where_params)
                            row = cursor.fetchone()
                        base_year = int(row[0]) if row else date.today().year
                    new_periodo = build_periodo(base_year, incoming.get(mes_key))
                    data[period_field] = new_periodo
                except Exception:
                    pass

        # No sobrescribir con NULL cuando llegan campos vacíos: solo actualizamos
        # los campos provistos con un valor distinto de None.
        data = {k: v for k, v in data.items() if v is not None}

        # Unicidad lógica para enfermedad_laboral durante PUT
        if getattr(self, "resource_name", None) == "enfermedad_laboral":
            # Obtener valores efectivos post-merge (usamos incoming->data + valores actuales si faltan)
            # Aquí validamos contra otros registros con distinto id
            enf_anio = data.get("anio", pk_values.get("anio") if "anio" in pk_values else None)
            enf_mes = data.get("mes", pk_values.get("mes") if "mes" in pk_values else None)
            enf_ind = data.get("indicador", incoming.get("indicador"))
            enf_cie = data.get("CODIGO CIE-10", incoming.get("CODIGO CIE-10"))
            enf_id = pk_values.get("id") or incoming.get("id")
            if enf_anio is not None and enf_mes is not None and enf_ind not in (None, ""):
                sql_dup = (
                    "SELECT 1 FROM talento_cultura.parametros_enfermedad_laboral "
                    "WHERE anio=%(anio)s AND mes=%(mes)s "
                    "AND upper(indicador)=upper(%(ind)s) "
                    "AND COALESCE(\"CODIGO CIE-10\", '') = COALESCE(%(cie)s, '') "
                    "AND id <> COALESCE(%(id)s, -1) LIMIT 1"
                )
                with connections['default'].cursor() as cursor:
                    cursor.execute(sql_dup, {"anio": enf_anio, "mes": enf_mes, "ind": enf_ind, "cie": enf_cie, "id": enf_id})
                    if cursor.fetchone():
                        return Response({"detail": "Registro duplicado (anio, mes, indicador, CIE-10)"}, status=status.HTTP_409_CONFLICT)
        set_parts = []
        for idx, (field, value) in enumerate(data.items()):
            param_key = f"val_{idx}"
            set_parts.append(f"{quote_identifier(field)} = %({param_key})s")
        if not set_parts:
            return Response({"detail": "No hay campos para actualizar"}, status=status.HTTP_400_BAD_REQUEST)
        params = {f"val_{idx}": value for idx, (field, value) in enumerate(data.items())}
        params.update(where_params)
        sql = f"UPDATE {resource['table']} SET {', '.join(set_parts)} WHERE {where_clause}"
        with transaction.atomic():
            with connections['default'].cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.rowcount == 0:
                    return Response({"detail": "No se encontró el registro a actualizar"}, status=status.HTTP_404_NOT_FOUND)
        select_sql = f"{resource['select']}\n WHERE {where_clause}"
        with connections['default'].cursor() as cursor:
            cursor.execute(select_sql, where_params)
            rows = fetch_dicts(cursor)
        return Response({"items": rows})

    def delete(self, request, *args, **kwargs):
        resource = self.get_resource()
        payload = prepare_payload(resource, request.data)
        try:
            pk_values = extract_pk(resource, payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        where_clause, params = build_where_from_pk(pk_values)
        sql = f"DELETE FROM {resource['table']} WHERE {where_clause}"
        with transaction.atomic():
            with connections['default'].cursor() as cursor:
                cursor.execute(sql, params)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AscensosView(TalentoResourceView):
    resource_name = "ascensos"


class BonosMensualView(TalentoResourceView):
    resource_name = "bonos_mensual"


class BonoCumpleView(TalentoResourceView):
    resource_name = "bono_cumple"


class ClimaLaboralView(TalentoResourceView):
    resource_name = "clima_laboral"


class DesempenoView(TalentoResourceView):
    resource_name = "desempeno"


class EgresosView(TalentoResourceView):
    resource_name = "egresos"


class RolLiderView(TalentoResourceView):
    resource_name = "rol_lider"


class ControlDisciplinarioView(TalentoResourceView):
    resource_name = "control_disciplinario"


class CapacitacionMensualView(TalentoResourceView):
    resource_name = "capacitacion_mensual"


class FormacionParticipacionView(TalentoResourceView):
    resource_name = "formacion_participacion"


class SatisfaccionAprendizajeView(TalentoResourceView):
    resource_name = "satisfaccion_aprendizaje"


class TransferenciaConocimientoView(TalentoResourceView):
    resource_name = "transferencia_conocimiento"


class AccidentalidadView(TalentoResourceView):
    resource_name = "accidentalidad"


class AusentismoView(TalentoResourceView):
    resource_name = "ausentismo"


class EnfermedadLaboralView(TalentoResourceView):
    resource_name = "enfermedad_laboral"


class PlanTrabajoView(TalentoResourceView):
    resource_name = "plan_trabajo"


class ProgramaCapacitacionesView(TalentoResourceView):
    resource_name = "programa_capacitaciones"


class ReporteMinisterioView(TalentoResourceView):
    resource_name = "reporte_ministerio"


class RestriccionesLaboralesView(TalentoResourceView):
    resource_name = "restricciones_laborales"


class EmpleadosView(TalentoResourceView):
    resource_name = "empleados"
