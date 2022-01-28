import datetime
import sqlalchemy as sa
from sqlalchemy.orm import relationship
import factory
from sqlalchemy.orm import scoped_session, sessionmaker


from SCCM.data.modelbase import SqlAlchemyBase


# each table needs to be represented by a class

class Prisoner(SqlAlchemyBase):
    __tablename__ = 'prisoners'

    id = sa.Column(sa.INT, primary_key=True, index=True)
    doc_num = sa.Column(sa.Integer, unique=True, index=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    judgment_name = sa.Column(sa.String, index=True)
    legal_name = sa.Column(sa.String, index=True)
    vendor_code = sa.Column(sa.String, nullable=True)

    cases_list = relationship("CourtCase", back_populates='prisoner')
    aliases = relationship('Alias', back_populates='prisoner_name')

    def __repr__(self):
        return '<Doc Number {}>'.format(self.doc_num)


class PrisonerFactory(factory.alchemy.SQLAlchemyModelFactory):
    doc_num = factory.Sequence(lambda n: n)
    created_date = datetime.datetime.today()
    updated_date = datetime.datetime.now()
    judgment_name = factory.Faker('name')

    class Meta:
        model = Prisoner
        # sqlalchemy_session = db_session
