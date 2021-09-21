import os
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional
import fuzz as fuzz
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from SCCM.data.court_cases import CourtCase
from SCCM.bin.balance import Balance
from SCCM.data.db_session import DbSession

cents = Decimal('0.01')


@dataclass
class Case:
    """
    A class used to track case information

    """
    case_number: str
    status: str
    overpayment: bool
    balance: Optional[Balance] = None
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
