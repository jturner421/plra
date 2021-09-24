from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import re

from SCCM.data.court_cases import CourtCase
from SCCM.models.balance import Balance
from SCCM.bin.transaction import Transaction
from SCCM.data.db_session import DbSession
from pydantic import BaseModel, ValidationError, validator, constr

cents = Decimal('0.01')


class Case(BaseModel):
    """
    A class used to track case information

    """
    case_number: constr(regex="[0-9][0-9]-[cv][cv]-[0-9]+$")
    status: str
    overpayment: bool
    balance: Optional[Balance] = None
    transaction: Optional[Transaction] = None
    case_search_dir: Optional[str] = None
    formatted_case_num: Optional[str] = None
    acct_cd: Optional[str] = None

    def create_case_db_object(self, db_session, doc_number) -> DbSession:
        db_session.add(CourtCase(prisoner_doc_num=doc_number,
                                 acct_cd=self.acct_cd,
                                 ecf_case_num=self.case_number,
                                 ccam_case_num=self.formatted_case_num,
                                 case_comment=self.status,
                                 amount_assessed=Decimal(self.balance.amount_assessed).quantize(cents,
                                                                                                ROUND_HALF_UP),
                                 amount_collected=Decimal(self.balance.amount_collected).quantize(cents,
                                                                                                  ROUND_HALF_UP),
                                 amount_owed=Decimal(self.balance.amount_owed).quantize(cents,
                                                                                        ROUND_HALF_UP)
                                 ))
        return db_session
