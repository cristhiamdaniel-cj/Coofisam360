EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS)
WITH ch AS (
    SELECT DISTINCT agencia_codigo AS codigo, anio, mes
    FROM saldos_agencia
    WHERE anio = 2025 AND mes = 8
),
agg AS (
    SELECT
        sa.agencia_codigo AS codigo,
        sa.anio,
        sa.mes,
        COALESCE(SUM(sa.saldo_final) FILTER (WHERE sa.cuenta::numeric = 14), 0) AS saldo_c14,
        COALESCE(SUM(sa.saldo_final) FILTER (WHERE sa.cuenta::numeric = 21), 0) AS saldo_c21
    FROM saldos_agencia sa
    JOIN ch ON ch.codigo = sa.agencia_codigo AND ch.anio = sa.anio AND ch.mes = sa.mes
    GROUP BY sa.agencia_codigo, sa.anio, sa.mes
)
SELECT codigo, anio, mes, saldo_c14, saldo_c21
FROM agg;
