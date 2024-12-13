from pathlib import Path

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from tests.vectorizer.extensions.conftest import load_template


def create_migration_script(migrations_dir: Path) -> None:
    """Create a basic migration script"""
    versions_dir = migrations_dir / "versions"
    migration_content = load_template(
        "migrations/001_create_test_table.py.template",
        revision_id="001",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )

    with open(versions_dir / "001_create_test_table.py", "w") as f:
        f.write(migration_content)


def create_vectorizer_migration_scripts(migrations_dir: Path) -> None:
    """Create migration scripts for vectorizer testing"""
    versions_dir = migrations_dir / "versions"

    # First migration - create blog table
    blog_content = load_template(
        "migrations/001_create_blog_table.py.template",
        revision_id="001",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )
    with open(versions_dir / "001_create_blog_table.py", "w") as f:
        f.write(blog_content)

    # Second migration - create vectorizer
    vectorizer_content = load_template(
        "migrations/002_create_vectorizer.py.template",
        revision_id="002",
        revises="001",
        create_date="2024-03-19 10:01:00.000000",
        down_revision="001",
    )
    with open(versions_dir / "002_create_vectorizer.py", "w") as f:
        f.write(vectorizer_content)


def test_basic_alembic_migration(alembic_config: Config, initialized_engine: Engine):
    """Verify basic Alembic functionality works before testing vectorizer operations"""
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_migration_script(migrations_dir)

    # Run upgrade
    upgrade(alembic_config, "head")

    # Verify table exists
    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "test_table" in tables

    # Check table structure
    columns = {
        col["name"]: col["type"].__class__.__name__
        for col in inspector.get_columns("test_table")
    }
    assert columns["id"] == "INTEGER"
    assert columns["name"] == "VARCHAR"

    # Run downgrade
    downgrade(alembic_config, "base")

    # Verify table is gone
    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "test_table" not in tables


def test_vectorizer_migration(
    alembic_config: Config,
    initialized_engine: Engine,
    cleanup_modules: None,  # noqa: ARG001
):
    """Test vectorizer creation and deletion via Alembic migrations"""
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_vectorizer_migration_scripts(migrations_dir)

    # Run upgrade to first migration (create blog table)
    upgrade(alembic_config, "001")

    # Verify blog table exists
    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "blog" in tables

    # Run upgrade to second migration (create vectorizer)
    upgrade(alembic_config, "002")

    # Verify vectorizer exists
    with initialized_engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM ai.vectorizer_status")).fetchone()
        assert result is not None
        assert result.source_table == "public.blog"
        assert result.pending_items == 0  # Since table is empty

    # Run downgrade of vectorizer
    downgrade(alembic_config, "001")

    # Verify vectorizer is gone but blog table remains
    with initialized_engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM ai.vectorizer_status")).fetchall()
        assert len(result) == 0

    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "blog" in tables

    # Run final downgrade
    downgrade(alembic_config, "base")

    # Verify everything is gone
    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "blog" not in tables


def create_complex_vectorizer_migration(migrations_dir: Path) -> None:
    """Create migration script for complex vectorizer testing"""
    versions_dir = migrations_dir / "versions"

    migration_content = load_template(
        "migrations/003_create_complex_vectorizer.py.template",
        revision_id="003",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )

    with open(versions_dir / "003_create_complex_vectorizer.py", "w") as f:
        f.write(migration_content)


def test_complex_vectorizer_migration(
    alembic_config: Config,
    initialized_engine: Engine,
    cleanup_modules: None,  # noqa: ARG001
):
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_complex_vectorizer_migration(migrations_dir)

    # Run upgrade
    upgrade(alembic_config, "head")

    # Verify articles table exists with all columns
    inspector = inspect(initialized_engine)
    tables = inspector.get_table_names()
    assert "articles" in tables

    # Verify vectorizer exists with correct configuration
    with initialized_engine.connect() as conn:
        # Check vectorizer status
        result = conn.execute(text("SELECT * FROM ai.vectorizer_status")).fetchone()
        assert result is not None
        assert result.source_table == "public.articles"
        assert result.pending_items == 0

        # Check specific vectorizer configuration
        vectorizer_config = conn.execute(
            text("SELECT * FROM ai.vectorizer WHERE source_table = 'articles'")
        ).fetchone()
        assert vectorizer_config is not None


def create_openai_vectorizer_migration(migrations_dir: Path) -> None:
    versions_dir = migrations_dir / "versions"
    migration_content = load_template(
        "migrations/004_create_openai_vectorizer.py.template",
        revision_id="004",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )
    with open(versions_dir / "004_create_openai_vectorizer.py", "w") as f:
        f.write(migration_content)


def create_ollama_vectorizer_migration(migrations_dir: Path) -> None:
    versions_dir = migrations_dir / "versions"
    migration_content = load_template(
        "migrations/005_create_ollama_vectorizer.py.template",
        revision_id="005",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )
    with open(versions_dir / "005_create_ollama_vectorizer.py", "w") as f:
        f.write(migration_content)


def create_hnsw_vectorizer_migration(migrations_dir: Path) -> None:
    """Create migration script for HNSW indexing vectorizer testing"""
    versions_dir = migrations_dir / "versions"
    migration_content = load_template(
        "migrations/006_create_hnsw_vectorizer.py.template",
        revision_id="006",
        revises="",
        create_date="2024-03-19 10:00:00.000000",
        down_revision="None",
    )
    with open(versions_dir / "006_create_hnsw_vectorizer.py", "w") as f:
        f.write(migration_content)


def test_openai_vectorizer_migration(
    alembic_config: Config,
    initialized_engine: Engine,
    cleanup_modules: None,  # noqa: ARG001
):
    """Test OpenAI vectorizer configuration"""
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_openai_vectorizer_migration(migrations_dir)

    upgrade(alembic_config, "head")

    with initialized_engine.connect() as conn:
        vectorizer_config = conn.execute(text("SELECT * FROM ai.vectorizer")).fetchone()
        assert vectorizer_config is not None
        config = str(dict(vectorizer_config._mapping))  # type: ignore
        assert "text-embedding-3-small" in config
        assert "768" in config
        assert "test_user" in config


def test_ollama_vectorizer_migration(
    alembic_config: Config,
    initialized_engine: Engine,
    cleanup_modules: None,  # noqa: ARG001
):
    """Test Ollama vectorizer configuration"""
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_ollama_vectorizer_migration(migrations_dir)

    upgrade(alembic_config, "head")

    with initialized_engine.connect() as conn:
        vectorizer_config = conn.execute(text("SELECT * FROM ai.vectorizer")).fetchone()
        assert vectorizer_config is not None
        config = str(dict(vectorizer_config._mapping))  # type: ignore
        assert "nomic-embed-text" in config
        assert "http://localhost:11434" in config


def test_hnsw_vectorizer_migration(
    alembic_config: Config,
    initialized_engine: Engine,
    cleanup_modules: None,  # noqa: ARG001
):
    """Test HNSW indexing vectorizer configuration"""
    migrations_dir = Path(alembic_config.get_main_option("script_location"))  # type: ignore
    create_hnsw_vectorizer_migration(migrations_dir)

    upgrade(alembic_config, "head")

    with initialized_engine.connect() as conn:
        vectorizer_config = conn.execute(text("SELECT * FROM ai.vectorizer")).fetchone()
        assert vectorizer_config is not None
        config = str(dict(vectorizer_config._mapping))  # type: ignore
        assert "vector_l1_ops" in config
        assert "16" in config  # m parameter
        assert "64" in config  # ef_construction
