import sqlalchemy
import sqlalchemy.orm
from SCCM.models.modelbase import SqlAlchemyBase
# noinspection PyUnresolvedReferences
import SCCM.models.__all_models

class DbSession:
    """
    Manages DB sessions.  This example is Sqlite specific.
    """
    factory = None
    engine = None

    @staticmethod
    def global_init(db_file: str):
        if DbSession.factory:
            return

        if not db_file or not db_file.strip():
            raise Exception("You must specify a models file.")

        conn_str = 'sqlite+pysqlite:///' + str(db_file)
        print(f'Connecting to {conn_str}')

        engine = sqlalchemy.create_engine(conn_str, connect_args={'check_same_thread': False},
                                          echo=True)  # set echo=True for debugging
        DbSession.engine = engine
        DbSession.factory = sqlalchemy.orm.sessionmaker(bind=engine)

        SqlAlchemyBase.metadata.create_all(engine)
        db_session = DbSession.factory()
        return db_session
