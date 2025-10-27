# Generated manually to add auto-increment ID field to fyc_formacion_snapshot

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('talento_cultura', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Add the id column as SERIAL (auto-increment)
            sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                ADD COLUMN id SERIAL;
            """,
            reverse_sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                DROP COLUMN id;
            """
        ),
        migrations.RunSQL(
            # Drop the existing composite primary key
            sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                DROP CONSTRAINT fyc_formacion_snapshot_pkey;
            """,
            reverse_sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                ADD CONSTRAINT fyc_formacion_snapshot_pkey 
                PRIMARY KEY (periodo, oficina_dependencia, rol_norm, tema_formacion, tipo_formacion);
            """
        ),
        migrations.RunSQL(
            # Add the new primary key on id
            sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                ADD CONSTRAINT fyc_formacion_snapshot_pkey 
                PRIMARY KEY (id);
            """,
            reverse_sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                DROP CONSTRAINT fyc_formacion_snapshot_pkey;
            """
        ),
        migrations.RunSQL(
            # Add unique constraint on the original composite key
            sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                ADD CONSTRAINT fyc_formacion_snapshot_unique_composite 
                UNIQUE (periodo, oficina_dependencia, rol_norm, tema_formacion, tipo_formacion);
            """,
            reverse_sql="""
                ALTER TABLE talento_cultura.fyc_formacion_snapshot 
                DROP CONSTRAINT fyc_formacion_snapshot_unique_composite;
            """
        ),
    ]

