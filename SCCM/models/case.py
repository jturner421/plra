from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import re

from SCCM.data.court_cases import CourtCase
from SCCM.models.balance import Balance
# from SCCM.models.person import PrisonerModel
from SCCM.bin.transaction import Transaction
from SCCM.data.db_session import DbSession
from pydantic import BaseModel, ValidationError, validator, constr

cents = Decimal('0.01')


class CaseBase(BaseModel):
    """
    A class used to track case information

    """
    ecf_case_num: constr(regex="[0-9][0-9]-[CV][CV]-[0-9]+$")
    status: str
    case_comment: str
    ccam_case_num: Optional[str] = None
    case_search_dir: Optional[str] = None

    def create_case_db_object(self, db_session, doc_number) -> DbSession:
        db_session.add(CourtCase(prisoner_doc_num=doc_number,
                                 acct_cd=self.acct_cd,
                                 ecf_case_num=self.ecf_case_num,
                                 ccam_case_num=self.ccam_case_num,
                                 case_comment=self.status,
                                 amount_assessed=Decimal(self.balance.amount_assessed).quantize(cents,
                                                                                                ROUND_HALF_UP),
                                 amount_collected=Decimal(self.balance.amount_collected).quantize(cents,
                                                                                                  ROUND_HALF_UP),
                                 amount_owed=Decimal(self.balance.amount_owed).quantize(cents,
                                                                                        ROUND_HALF_UP)
                                 ))
        return db_session


class CaseCreate(CaseBase):
    pass


class CaseModel(CaseBase):
    id: int
    prisoner_doc_num: int
    acct_cd: Optional[str] = None
    amount_assessed: Decimal
    amount_collected: Decimal
    amount_owed: Decimal
    transaction: Optional[Transaction] = None
    # prisoner: PrisonerModel

    class Config:
        orm_mode = True
