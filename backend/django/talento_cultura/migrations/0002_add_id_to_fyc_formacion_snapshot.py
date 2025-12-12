# Generated manually to add auto-increment ID field to fyc_formacion_snapshot

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('talento_cultura', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Asegurar esquema y cambios sólo si existe la tabla objetivo
                CREATE SCHEMA IF NOT EXISTS talento_cultura;
                DO $$
                BEGIN
                  IF to_regclass('talento_cultura.fyc_formacion_snapshot') IS NOT NULL THEN
                    -- 1) Agregar columna id si no existe
                    BEGIN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot ADD COLUMN id SERIAL;
                    EXCEPTION WHEN duplicate_column THEN
                      -- ignorar si ya existe
                      NULL;
                    END;

                    -- 2) Quitar PK compuesta si existe
                    IF EXISTS (
                      SELECT 1 FROM pg_constraint 
                      WHERE conname = 'fyc_formacion_snapshot_pkey' 
                        AND conrelid = 'talento_cultura.fyc_formacion_snapshot'::regclass
                    ) THEN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot DROP CONSTRAINT fyc_formacion_snapshot_pkey;
                    END IF;

                    -- 3) Crear PK sobre id si no existe
                    IF NOT EXISTS (
                      SELECT 1 FROM pg_constraint 
                      WHERE conname = 'fyc_formacion_snapshot_pkey' 
                        AND conrelid = 'talento_cultura.fyc_formacion_snapshot'::regclass
                    ) THEN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot
                        ADD CONSTRAINT fyc_formacion_snapshot_pkey PRIMARY KEY (id);
                    END IF;

                    -- 4) Crear unique sobre la clave compuesta si no existe
                    IF NOT EXISTS (
                      SELECT 1 FROM pg_constraint 
                      WHERE conname = 'fyc_formacion_snapshot_unique_composite' 
                        AND conrelid = 'talento_cultura.fyc_formacion_snapshot'::regclass
                    ) THEN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot
                        ADD CONSTRAINT fyc_formacion_snapshot_unique_composite
                        UNIQUE (periodo, oficina_dependencia, rol_norm, tema_formacion, tipo_formacion);
                    END IF;
                  END IF;
                END
                $$;
            """,
            reverse_sql="""
                -- Reversión segura: sólo si existen objetos
                DO $$
                BEGIN
                  IF to_regclass('talento_cultura.fyc_formacion_snapshot') IS NOT NULL THEN
                    IF EXISTS (
                      SELECT 1 FROM pg_constraint 
                      WHERE conname = 'fyc_formacion_snapshot_unique_composite' 
                        AND conrelid = 'talento_cultura.fyc_formacion_snapshot'::regclass
                    ) THEN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                        DROP CONSTRAINT fyc_formacion_snapshot_unique_composite;
                    END IF;
                    IF EXISTS (
                      SELECT 1 FROM pg_constraint 
                      WHERE conname = 'fyc_formacion_snapshot_pkey' 
                        AND conrelid = 'talento_cultura.fyc_formacion_snapshot'::regclass
                    ) THEN
                      ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                        DROP CONSTRAINT fyc_formacion_snapshot_pkey;
                    END IF;
                    -- no eliminar columna id para evitar pérdida de datos
                  END IF;
                END
                $$;
            """,
        ),
    ]
