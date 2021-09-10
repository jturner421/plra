import sqlalchemy
import sqlalchemy.orm
from SCCM.data.modelbase import SqlAlchemyBase
from pathlib import Path
# noinspection PyUnresolvedReferences
import SCCM.data.__all_models


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

        # if not db_file or not db_file.strip():
        #     raise Exception("You must specify a data file.")

        # TODO: refactor to manage dev and prod connections
        conn_str = 'sqlite:///' + str(db_file)
        print(f'Connecting to {conn_str}')

        # engine = sqlalchemy.create_engine(conn_str, echo=False)  # set echo=True for debugging
        engine = sqlalchemy.create_engine(conn_str, connect_args={'check_same_thread': False}, echo=False)  # set echo=True for debugging
        DbSession.engine = engine
        DbSession.factory = sqlalchemy.orm.sessionmaker(bind=engine)

        SqlAlchemyBase.metadata.create_all(engine)
        db_session = DbSession.factory()
        return db_session
