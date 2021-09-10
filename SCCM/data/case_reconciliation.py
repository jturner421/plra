import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from SCCM.data.court_cases import CourtCase
from SCCM.data.modelbase import SqlAlchemyBase


class CaseReconciliation(SqlAlchemyBase):
    __tablename__ = 'case_reconciliation'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    court_case_id = sa.Column(sa.Integer, sa.ForeignKey('court_cases.id'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date =  sa.Column(sa.DateTime, onupdate=datetime.datetime.now)
    previous_amount_assessed = sa.Column(sa.NUMERIC, nullable=False)
    previous_amount_collected = sa.Column(sa.NUMERIC, nullable=False)
    previous_amount_owed = sa.Column(sa.NUMERIC, nullable=False)
    updated_amount_assessed = sa.Column(sa.NUMERIC, nullable=False)
    updated_amount_collected = sa.Column(sa.NUMERIC, nullable=False)
    updated_amount_owed = sa.Column(sa.NUMERIC, nullable=False)
    # case_recon = orm.relationship("CourtCase", back_populates="case_reconciliation")


# CourtCase.case_reconciliation = orm.relationship("CaseReconciliation", back_populates="case_recon")