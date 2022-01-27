import datetime
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from SCCM.data.modelbase import SqlAlchemyBase
from SCCM.data.prisoners import Prisoner


class CourtCase(SqlAlchemyBase):
    __tablename__ = 'court_cases'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    #prisoner_doc_num = sa.Column(sa.Integer, sa.ForeignKey('prisoners.doc_num'))
    prisoner_id = sa.Column(sa.Integer, sa.ForeignKey('prisoners.id'))
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    acct_cd = sa.Column(sa.String, nullable=True)
    ecf_case_num = sa.Column(sa.String)
    ccam_case_num = sa.Column(sa.String)
    case_comment = sa.Column(sa.String, nullable=True)
    balance_created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    balance_updated_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    amount_assessed = sa.Column(sa.NUMERIC, nullable=False)
    amount_collected = sa.Column(sa.NUMERIC, nullable=False)
    amount_owed = sa.Column(sa.NUMERIC, nullable=False)
    prisoner = relationship("Prisoner", back_populates='cases')

    def __repr__(self):
        return f'<Case Number {self.ecf_case_num} - Balance = {self.amount_owed}>'


