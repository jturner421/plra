# file that is needed for SqlAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

# see https://alembic.sqlalchemy.org/en/latest/naming.html#autogen-naming-conventions
meta = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })
# Creates singleton base class that "registers" DB classes
SqlAlchemyBase = declarative_base(metadata=meta)
