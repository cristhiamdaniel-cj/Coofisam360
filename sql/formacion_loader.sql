-- Loader para formación: inserta datos a formacion_participacion
-- Deja la vista T_FYC_FORMACION funcionando sin cambios.

BEGIN;
SET search_path TO talento_cultura, public;

CREATE EXTENSION IF NOT EXISTS unaccent;

-- Staging opcional para pegar CSVs
CREATE TABLE IF NOT EXISTS talento_cultura.formacion_participacion_input (
  id                       bigserial PRIMARY KEY,
  anio                     int       NOT NULL,
  mes_texto                text      NOT NULL,
  oficina_dependencia      text      NOT NULL,
  rol                      text      NOT NULL,
  tema_formacion           text      NOT NULL,
  tipo_formacion           text      NOT NULL,
  cant_trab_participaron   int       NOT NULL,
  total_participantes      int       NOT NULL,
  veces_formado            int,
  calificacion             numeric(3,2),
  grupo                    smallint  NOT NULL DEFAULT 1
);

-- Helper: mes en español a número
CREATE OR REPLACE FUNCTION talento_cultura.fn_mes_texto_a_num(mes text)
RETURNS int LANGUAGE plpgsql AS $$
DECLARE
  m text := upper(unaccent(trim(mes)));
BEGIN
  CASE m
    WHEN 'ENERO' THEN RETURN 1;
    WHEN 'FEBRERO' THEN RETURN 2;
    WHEN 'MARZO' THEN RETURN 3;
    WHEN 'ABRIL' THEN RETURN 4;
    WHEN 'MAYO' THEN RETURN 5;
    WHEN 'JUNIO' THEN RETURN 6;
    WHEN 'JULIO' THEN RETURN 7;
    WHEN 'AGOSTO' THEN RETURN 8;
    WHEN 'SEPTIEMBRE', 'SETIEMBRE' THEN RETURN 9;
    WHEN 'OCTUBRE' THEN RETURN 10;
    WHEN 'NOVIEMBRE' THEN RETURN 11;
    WHEN 'DICIEMBRE' THEN RETURN 12;
    ELSE RAISE EXCEPTION 'Mes no reconocido: %', mes;
  END CASE;
END$$;

-- Upsert desde staging a la tabla base que usa la vista
CREATE OR REPLACE FUNCTION talento_cultura.fn_cargar_formacion_desde_input()
RETURNS void LANGUAGE sql AS $$
INSERT INTO talento_cultura.formacion_participacion (
  periodo, oficina_dependencia, rol, tema_formacion, tipo_formacion,
  cant_trab_participaron, total_participantes, veces_formado, calificacion, grupo
)
SELECT
  make_date(anio, talento_cultura.fn_mes_texto_a_num(mes_texto), 1) AS periodo,
  oficina_dependencia,
  rol,
  tema_formacion,
  tipo_formacion,
  cant_trab_participaron,
  total_participantes,
  COALESCE(veces_formado, 1),
  calificacion,
  COALESCE(grupo, 1)
FROM talento_cultura.formacion_participacion_input i
ON CONFLICT (periodo, oficina_dependencia, rol, tema_formacion, tipo_formacion, grupo)
DO UPDATE SET
  cant_trab_participaron = EXCLUDED.cant_trab_participaron,
  total_participantes    = EXCLUDED.total_participantes,
  veces_formado          = EXCLUDED.veces_formado,
  calificacion           = EXCLUDED.calificacion
$$;

COMMIT;

-- Ejemplo de uso:
-- 1) Cargar CSV a staging (ruta del repo):
--    \copy talento_cultura.formacion_participacion_input(
--      anio, mes_texto, cant_trab_participaron, oficina_dependencia, rol, tema_formacion,
--      tipo_formacion, total_participantes, veces_formado, calificacion, grupo)
--      FROM 'data/formacion_input.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
-- 2) Upsert a la tabla base:
--    SELECT talento_cultura.fn_cargar_formacion_desde_input();
