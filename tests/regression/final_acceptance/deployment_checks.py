"""Synthetic schema upgrade probe; never connects to configured/live database."""
from sqlalchemy import create_engine, inspect, text


def test_existing_case_schema_gains_owner_id(modules, tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'legacy.sqlite'))
    try:
        with engine.begin() as c:
            c.execute(text('CREATE TABLE cases (id VARCHAR(36) PRIMARY KEY, title VARCHAR(200) NOT NULL, merchant_name VARCHAR(200) NOT NULL, status VARCHAR(50) NOT NULL, version INTEGER NOT NULL, resolution_note TEXT, resolved_at VARCHAR(50), created_at VARCHAR(50) NOT NULL)'))
        # This is exactly the schema initialization operation used by production lifespan.
        modules[1].Base.metadata.create_all(bind=engine)
        assert 'owner_id' in {x['name'] for x in inspect(engine).get_columns('cases')}, 'create_all does not migrate existing cases; owner_id upgrade/backfill is missing'
    finally:
        engine.dispose()
