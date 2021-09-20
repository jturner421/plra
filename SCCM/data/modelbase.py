# file that is needed for SqlAlchemy
from sqlalchemy.orm import declarative_base

# Creates singleton base class that "registers" DB classes
SqlAlchemyBase = declarative_base()
