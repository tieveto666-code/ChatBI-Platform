from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models.base import Base
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DATABASE_ECHO,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """首次启动时自动创建所有表"""
    from services.table_synonym_service import migrate_legacy_table_synonyms

    migrate_legacy_table_synonyms(engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    db = SessionLocal()
    try:
        from services.agent_service import ensure_default_agent
        ensure_default_agent(db)
    finally:
        db.close()


def ensure_schema_columns():
    """MVP 轻量迁移：为已有 SQLite 库补齐新增列。"""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    columns_to_add = {
        "file_uploads": {
            "query_db_path": "VARCHAR(512)",
            "created_by": "INTEGER",
            "visibility": "VARCHAR(16) DEFAULT 'private'",
        },
        "file_sheets": {
            "name_mapping_json": "TEXT",
        },
        "conversations": {
            "selected_tables": "TEXT",
        },
        "agent_configs": {
            "created_by": "INTEGER",
            "visibility": "VARCHAR(16) DEFAULT 'private'",
            "default_data_source_type": "VARCHAR(16)",
            "default_db_connection_id": "INTEGER",
            "default_file_upload_id": "INTEGER",
            "workflow_config": "TEXT",
        },
        "db_connections": {
            "created_by": "INTEGER",
            "visibility": "VARCHAR(16) DEFAULT 'private'",
        },
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table_name, columns in columns_to_add.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def get_db():
    """FastAPI 依赖注入：获取数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
