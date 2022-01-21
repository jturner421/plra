from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel
from SCCM.models.case import CaseModel


class PrisonerBase(BaseModel):
    doc_num: int
    check_name: str
    amount_paid: Decimal


class PrisonerCreate(PrisonerBase):
    judgment_name: Optional[str] = None
    pty_code: Optional[str] = None
    cases_list: List = []
    search_dir: Optional[str] = None
    case_search_dir: Optional[str] = None
    overpayment: str = None


class PrisonerModel(PrisonerBase):
    id: int
    cases: Optional[List[CaseModel]] = None

    class Config:
        orm_mode = True
