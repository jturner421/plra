import datetime
import sqlalchemy as sa
from sqlalchemy import orm

from SCCM.data.modelbase import SqlAlchemyBase
from SCCM.data.prisoners import Prisoner


class CourtCase(SqlAlchemyBase):
    __tablename__ = 'court_cases'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    prisoner_doc_num = sa.Column(sa.Integer, sa.ForeignKey('prisoners.doc_num'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    acct_cd = sa.Column(sa.String, nullable=True)
    case_num = sa.Column(sa.String)
    case_comment = sa.Column(sa.String, nullable=True)
    prisoner = orm.relationship("Prisoner", back_populates='court_cases')

    def __repr__(self):
        return '<Case Number {}>'.format(self.case_num)


Prisoner.court_cases = orm.relationship("CourtCase",back_populates="prisoner")

