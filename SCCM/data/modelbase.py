# file that is needed for SqlAlchemy
import sqlalchemy.ext.declarative as dec

# Creates singleton base class that "registers" DB classes
SqlAlchemyBase = dec.declarative_base()
