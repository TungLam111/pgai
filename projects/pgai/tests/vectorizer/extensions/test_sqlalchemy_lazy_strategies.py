from _pytest.logging import LogCaptureFixture
from click.testing import CliRunner
from sqlalchemy import Column, Engine, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import text
from testcontainers.postgres import PostgresContainer  # type: ignore

from pgai.cli import vectorizer_worker
from pgai.sqlalchemy import embedding_relationship


class Base(DeclarativeBase):
    pass


class ArticleWithLazyStrategies(Base):
    __tablename__ = "articles_lazy_test"
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)

    # Different vectorizers with different lazy loading strategies
    embeddings = embedding_relationship(dimensions=768, lazy="joined")


def test_joined_loading(
    postgres_container: PostgresContainer,
    initialized_engine: Engine,
    caplog: LogCaptureFixture,
):
    """Test the difference between select and joined loading strategies."""
    db_url = postgres_container.get_connection_url()

    # Create tables

    metadata = ArticleWithLazyStrategies.metadata
    metadata.create_all(initialized_engine, tables=[metadata.sorted_tables[0]])

    # Create vectorizers in database
    with initialized_engine.connect() as conn:
        conn.execute(
            text("""
                SELECT ai.create_vectorizer(
                    'articles_lazy_test'::regclass,
                    embedding => ai.embedding_openai('text-embedding-3-small', 768),
                    chunking =>
                    ai.chunking_recursive_character_text_splitter('content', 50, 10)
                );
                """)
        )
        conn.commit()

    # Insert test data
    with Session(initialized_engine) as session:
        articles: list[ArticleWithLazyStrategies] = []
        for i in range(3):
            article = ArticleWithLazyStrategies(
                title=f"Test Article {i}",
                content=f"This is test content {i} that will be embedded.",
            )
            session.add(article)
            articles.append(article)
            # _ = article.embeddings
        session.commit()

    # Run vectorizer worker for each vectorizer
    for i in range(1, 3):
        CliRunner().invoke(
            vectorizer_worker,
            [
                "--db-url",
                db_url,
                "--once",
                "--vectorizer-id",
                str(i),
                "--concurrency",
                "1",
            ],
            catch_exceptions=False,
        )

    with (
        Session(initialized_engine) as session,
        caplog.at_level("DEBUG", "sqlalchemy.engine"),
    ):
        articles = session.query(ArticleWithLazyStrategies).all()

        initial_queries = [r.message for r in caplog.records if "SELECT" in r.message]
        _ = [article.embeddings[0].chunk for article in articles]
        after_select_queries = [
            r.message for r in caplog.records if "SELECT" in r.message
        ]
        assert len(after_select_queries) == len(initial_queries), (
            f"Should not trigger additional queries"
            f" but queries were: {after_select_queries}"
        )
