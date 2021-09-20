import datetime
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from SCCM.data.modelbase import SqlAlchemyBase
from SCCM.data.prisoners import Prisoner


class Alias(SqlAlchemyBase):
    __tablename__ = 'alias'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    prisoner_doc_num = sa.Column(sa.Integer, sa.ForeignKey('prisoners.doc_num'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    alias_name = sa.Column(sa.String)
    prisoner_name = relationship("Prisoner", back_populates='aliases')

    def __repr__(self):
        return '<Case Number {}>'.format(self.case_num)


