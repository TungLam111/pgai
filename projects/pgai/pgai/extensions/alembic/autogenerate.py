from typing import Any

from alembic.autogenerate import comparators
from sqlalchemy import  text

from pgai.extensions.alembic.operations import EmbeddingConfig, ChunkingConfig, FormattingConfig, CreateVectorizerOp, \
    DropVectorizerOp, IndexingConfig, SchedulingConfig, ProcessingConfig


@comparators.dispatch_for("schema")
def compare_vectorizers(autogen_context, upgrade_ops, schemas):
    """Compare vectorizers between model and database, generating appropriate migration operations.

    Handles creation, updates and deletion of vectorizers by comparing the current database
    state with the model definitions.
    """
    print("Running vectorizer comparator!")  # Debug print

    conn = autogen_context.connection

    # Get existing vectorizers with their full configuration from database
    existing_vectorizers: dict[str, dict[str, Any]] = {}
    for schema in schemas:
        result = conn.execute(text("""
            SELECT 
                v.id,
                v.source_schema,
                v.source_table,
                v.target_schema,
                v.target_table,
                v.view_schema, 
                v.view_name,
                v.queue_schema,
                v.queue_table,
                v.config
            FROM ai.vectorizer v 
            WHERE v.source_schema = :schema
        """), {"schema": schema or "public"}).fetchall()

        for row in result:
            source_table = f"{row.source_schema}.{row.source_table}"
            existing_vectorizers[source_table] = {
                'id': row.id,
                'source_schema': row.source_schema,
                'source_table': row.source_table,
                'target_schema': row.target_schema,
                'target_table': row.target_table,
                'view_schema': row.view_schema,
                'view_name': row.view_name,
                'queue_schema': row.queue_schema,
                'queue_table': row.queue_table,
                'config': row.config
            }

    # Get vectorizers from models
    model_vectorizers: dict[str, dict[str, Any]] = {}
    if hasattr(autogen_context.metadata, "info"):
        vectorizers = autogen_context.metadata.info.get("vectorizers", {})
        for key, config in vectorizers.items():
            source_table = config["source_table"]
            if "." not in source_table:
                source_table = f"public.{source_table}"
            model_vectorizers[source_table] = config

    # Compare and generate operations
    for table_name, model_config in model_vectorizers.items():
        if table_name not in existing_vectorizers:
            # Create new vectorizer
            upgrade_ops.ops.append(
                CreateVectorizerOp(
                    source_table=model_config["source_table"],
                    destination=model_config.get("destination"),
                    embedding=EmbeddingConfig(**model_config["embedding"]),
                    chunking=ChunkingConfig(**model_config["chunking"]),
                    formatting=FormattingConfig(
                        **model_config.get("formatting", {})) if "formatting" in model_config else None,
                    indexing=IndexingConfig(**model_config.get("indexing", {})) if "indexing" in model_config else None,
                    scheduling=SchedulingConfig(
                        **model_config.get("scheduling", {})) if "scheduling" in model_config else None,
                    processing=ProcessingConfig(
                        **model_config.get("processing", {})) if "processing" in model_config else None,
                    target_schema=model_config.get("target_schema"),
                    target_table=model_config.get("target_table"),
                    view_schema=model_config.get("view_schema"),
                    view_name=model_config.get("view_name"),
                    queue_schema=model_config.get("queue_schema"),
                    queue_table=model_config.get("queue_table"),
                )
            )
        else:
            # Check for configuration changes
            existing_config = existing_vectorizers[table_name]
            if _config_has_changed(model_config, existing_config):
                # Drop and recreate vectorizer if config changed
                upgrade_ops.ops.extend([
                    DropVectorizerOp(
                        existing_config["id"],
                        drop_objects=True,
                    ),
                    CreateVectorizerOp(
                        source_table=model_config["source_table"],
                        destination=model_config.get("destination"),
                        embedding=EmbeddingConfig(**model_config["embedding"]),
                        chunking=ChunkingConfig(**model_config["chunking"]),
                        formatting=FormattingConfig(
                            **model_config.get("formatting", {})) if "formatting" in model_config else None,
                        indexing=IndexingConfig(
                            **model_config.get("indexing", {})) if "indexing" in model_config else None,
                        scheduling=SchedulingConfig(
                            **model_config.get("scheduling", {})) if "scheduling" in model_config else None,
                        processing=ProcessingConfig(
                            **model_config.get("processing", {})) if "processing" in model_config else None,
                        target_schema=model_config.get("target_schema"),
                        target_table=model_config.get("target_table"),
                        view_schema=model_config.get("view_schema"),
                        view_name=model_config.get("view_name"),
                        queue_schema=model_config.get("queue_schema"),
                        queue_table=model_config.get("queue_table"),
                    )
                ])

    for table_name, existing_config in existing_vectorizers.items():
        if table_name not in model_vectorizers:
            upgrade_ops.ops.append(
                DropVectorizerOp(
                    existing_config["id"],
                    drop_objects=True,
                )
            )


def _config_has_changed(model_config: dict[str, Any], existing_config: dict[str, Any]) -> bool:
    """Compare vectorizer configurations to detect changes.

    Returns True if any configuration parameters have changed.
    """
    # Compare core components
    config_keys = {'embedding', 'chunking', 'formatting', 'indexing', 'scheduling', 'processing'}
    for key in config_keys:
        model_value = model_config.get(key)
        existing_value = existing_config['config'].get(key) if existing_config.get('config') else None

        if model_value is None and existing_value is None:
            continue

        if model_value != existing_value:
            return True

    # Compare schema/table settings
    schema_keys = {
        'target_schema', 'target_table', 'view_schema', 'view_name',
        'queue_schema', 'queue_table'
    }

    for key in schema_keys:
        model_value = model_config.get(key)
        existing_value = existing_config.get(key)

        if model_value is None and existing_value is None:
            continue

        if model_value != existing_value:
            return True

    return False


def _filter_config_fields(config: dict[str, Any]) -> dict[str, Any]:
    """Remove internal config metadata fields that aren't part of the dataclass definitions"""
    filtered = config.copy()
    filtered.pop('config_type', None)
    filtered.pop('implementation', None)
    return filtered


def _config_to_op_params(db_vectorizer: dict[str, Any]) -> dict[str, Any]:
    """Convert vectorizer database record into CreateVectorizerOp parameters"""
    config = db_vectorizer['config']

    # Build source table reference 
    source_table = f"{db_vectorizer['source_schema']}.{db_vectorizer['source_table']}"

    # Extract configs into appropriate dataclasses, filtering internal fields
    embedding = EmbeddingConfig(**_filter_config_fields(config['embedding'])) if 'embedding' in config else None
    chunking = ChunkingConfig(**_filter_config_fields(config['chunking'])) if 'chunking' in config else None
    formatting = FormattingConfig(**_filter_config_fields(config['formatting'])) if 'formatting' in config else None
    indexing = IndexingConfig(**_filter_config_fields(config['indexing'])) if 'indexing' in config else None
    scheduling = SchedulingConfig(**_filter_config_fields(config['scheduling'])) if 'scheduling' in config else None
    processing = ProcessingConfig(**_filter_config_fields(config['processing'])) if 'processing' in config else None

    # Build complete params dict
    params = {
        'source_table': source_table,
        'destination': None,  # Derived from target info
        'embedding': embedding,
        'chunking': chunking,
        'formatting': formatting,
        'indexing': indexing,
        'scheduling': scheduling,
        'processing': processing,
        'target_schema': db_vectorizer['target_schema'],
        'target_table': db_vectorizer['target_table'],
        'view_schema': db_vectorizer['view_schema'],
        'view_name': db_vectorizer['view_name'],
        'queue_schema': db_vectorizer['queue_schema'],
        'queue_table': db_vectorizer['queue_table']
    }

    return params
