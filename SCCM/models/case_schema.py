from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import re

from SCCM.data.court_cases import CourtCase
from SCCM.models.balance import Balance
import SCCM.models.transaction_schema as ts
# from SCCM.models.person import PrisonerModel

from SCCM.data.db_session import DbSession
from pydantic import BaseModel, ValidationError, validator, constr

cents = Decimal('0.01')


class CaseBase(BaseModel):
    """
    A class used to track case information

    """
    ecf_case_num: constr(regex="[0-9][0-9]-[CV][CV]-[0-9]+$")
    comment: str


class CaseCreate(CaseBase):
    acct_cd: Optional[str] = None
    ccam_case_num: Optional[str] = None
    case_party_number: Optional[str] = None
    balance: Optional[Balance] = None
    transaction: Optional[ts.TransactionModel] = None


class CaseModel(CaseBase):
    id: int
    prisoner_doc_num: int
    acct_cd: Optional[str] = None
    amount_assessed: Decimal
    amount_collected: Decimal
    amount_owed: Decimal
    transaction: Optional[ts.TransactionModel] = None

    # prisoner: PrisonerModel

    class Config:
        orm_mode = True
