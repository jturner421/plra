from decimal import Decimal
from typing import Optional

from SCCM.models.balance import Balance
import SCCM.models.transaction_schema as ts
# from SCCM.models.person import PrisonerModel

from pydantic import BaseModel, constr

cents = Decimal('0.01')


class CaseBase(BaseModel):
    """
    A class used to track case information

    """
    ecf_case_num: constr(regex="[0-9][0-9]-[CV][CV]-[0-9]+$")
    case_comment: str


class CaseCreate(CaseBase):
    acct_cd: Optional[str] = None
    ccam_case_num: Optional[str] = None
    case_party_number: Optional[str] = None
    balance: Optional[Balance] = None
    transaction: Optional[ts.TransactionModel] = None


class CaseModel(CaseBase):
    id: int
    prisoner_id: int
    acct_cd: Optional[str] = None
    ccam_case_num:str
    amount_assessed: Decimal
    amount_collected: Decimal
    amount_owed: Decimal
    balance: Optional[Balance] = None
    transaction: Optional[ts.TransactionModel] = None

    class Config:
        orm_mode = True
