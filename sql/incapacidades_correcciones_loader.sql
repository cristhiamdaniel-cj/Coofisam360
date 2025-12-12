-- Correcciones de diagnósticos y datos faltantes para incapacidades (desde Excel externo)
-- Usa documento + fecha_inicio (+opcional fecha_fin) para ubicar el registro en BUK y actualizar diagnostico_codigo.

BEGIN;
SET search_path TO talento_cultura, public;

CREATE TABLE IF NOT EXISTS talento_cultura.incapacidades_correcciones_input (
  doc                         text      NOT NULL,
  fecha_inicio                date      NOT NULL,
  fecha_fin                   date,
  diagnostico_codigo_nuevo    text,
  dias_tomados               numeric(10,2)
);

-- Aplica correcciones contra incapacidades_buk_staging
CREATE OR REPLACE FUNCTION talento_cultura.fn_aplicar_correcciones_incap()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  -- Actualiza diagnostico_codigo por match de documento y fecha_inicio (y opcional fecha_fin)
  UPDATE talento_cultura.incapacidades_buk_staging i
    SET diagnostico_codigo = ci.diagnostico_codigo_nuevo
  FROM talento_cultura.incapacidades_correcciones_input ci
  JOIN talento_cultura.informacion_laboral_buk_staging s
    ON s.empleado_numero_de_documento = ci.doc
  WHERE s.buk_employee_id = i.buk_employee_id
    AND i.fecha_inicio = ci.fecha_inicio
    AND (ci.fecha_fin IS NULL OR i.fecha_fin = ci.fecha_fin)
    AND ci.diagnostico_codigo_nuevo IS NOT NULL
    AND (i.diagnostico_codigo IS DISTINCT FROM ci.diagnostico_codigo_nuevo);
END;$$;

COMMIT;

-- Ejemplo de carga desde CSV (ajusta ruta):
-- \copy talento_cultura.incapacidades_correcciones_input(doc, fecha_inicio, fecha_fin, diagnostico_codigo_nuevo, dias_tomados)
--   FROM 'data/incapacidades_correcciones.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
-- SELECT talento_cultura.fn_aplicar_correcciones_incap();
