import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from SCCM.data.court_cases import CourtCase
from SCCM.data.modelbase import SqlAlchemyBase


class CaseBalance(SqlAlchemyBase):
    __tablename__ = 'case_balance'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    court_case_id = sa.Column(sa.Integer, sa.ForeignKey('court_cases.id'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date =  sa.Column(sa.DateTime, onupdate=datetime.datetime.now)
    amount_assessed = sa.Column(sa.NUMERIC, nullable=False)
    amount_collected = sa.Column(sa.NUMERIC, nullable=False)
    amount_owed = sa.Column(sa.NUMERIC, nullable=False)
    case = orm.relationship("CourtCase", back_populates="case_balance")


CourtCase.case_balance = orm.relationship("CaseBalance", back_populates="case")