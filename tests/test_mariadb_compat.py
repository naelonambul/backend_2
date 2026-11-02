from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.db.database import Base
from app.models import board, payment_reconciliation, property, purchase, question, social_account, user  # noqa: F401


def test_all_application_tables_compile_for_mariadb():
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=mysql.dialect()))


def test_mariadb_purchase_index_only_applies_to_active_orders():
    statements = []
    engine = None

    def collect(sql, *multiparams, **params):
        statements.append(str(sql.compile(dialect=engine.dialect)))

    engine = create_mock_engine('mysql+pymysql://', collect)
    Base.metadata.create_all(engine)
    purchase_statements = '\n'.join(statements)

    assert "CASE WHEN status IN ('pending', 'paid', 'refund_pending')" in purchase_statements
    assert 'ELSE NULL END' in purchase_statements
    assert 'UNIQUE' in purchase_statements
    assert 'uq_purchase_active_property' in purchase_statements
    assert 'CREATE UNIQUE INDEX uq_purchase_active_property ON purchase (property_idx)' not in purchase_statements
