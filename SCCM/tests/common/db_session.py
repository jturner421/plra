from sqlalchemy import create_engine
import sqlalchemy
import sqlalchemy.orm

from SCCM.data.modelbase import SqlAlchemyBase
import SCCM.data.__all_models


class TestDbSession:
    factory = None
    engine = None

    @staticmethod
    def global_init():
        if TestDbSession.factory:
            return
        engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, echo=True)
        TestDbSession.engine = engine
        TestDbSession.factory = sqlalchemy.orm.sessionmaker(bind=engine)
        SqlAlchemyBase.metadata.create_all(engine)
        db_session = TestDbSession.factory()
        return db_session

