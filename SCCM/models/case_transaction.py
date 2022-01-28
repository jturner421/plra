import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relationship, backref

from SCCM.models.court_cases import CourtCase
from SCCM.models.modelbase import SqlAlchemyBase


class CaseTransaction(SqlAlchemyBase):
    __tablename__ = 'case_transactions'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    court_case_id = sa.Column(sa.Integer, sa.ForeignKey('court_cases.id'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date = sa.Column(sa.DateTime, onupdate=datetime.datetime.now)
    check_number= sa.Column(sa.INT, nullable=False)
    amount_paid = sa.Column(sa.NUMERIC, nullable=False)
    case_tran = relationship("CourtCase", back_populates="case_transactions")


CourtCase.case_transactions = relationship("CaseTransaction", order_by=CaseTransaction.id, back_populates="case_tran")


