from django.db import migrations


def create_fts_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS norm_fts_gin_idx
        ON knowledge_norm USING GIN(
            to_tsvector('russian',
                coalesce(title, '') || ' ' ||
                coalesce(article, '') || ' ' ||
                coalesce(text, ''))
        )
    """)
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS courtcase_fts_gin_idx
        ON knowledge_courtcase USING GIN(
            to_tsvector('russian',
                coalesce(case_number, '') || ' ' ||
                coalesce(thesis, '') || ' ' ||
                coalesce(text, ''))
        )
    """)
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS legalopinion_fts_gin_idx
        ON knowledge_legalopinion USING GIN(
            to_tsvector('russian',
                coalesce(title, '') || ' ' ||
                coalesce(text, ''))
        )
    """)


def drop_fts_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS norm_fts_gin_idx")
    schema_editor.execute("DROP INDEX IF EXISTS courtcase_fts_gin_idx")
    schema_editor.execute("DROP INDEX IF EXISTS legalopinion_fts_gin_idx")


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_fts_indexes, drop_fts_indexes),
    ]
