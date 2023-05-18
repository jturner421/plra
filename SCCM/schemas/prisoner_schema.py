from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel
from SCCM.schemas.case_schema import CaseModel


class PrisonerBase(BaseModel):
    doc_num: int
    legal_name: str
    amount_paid: Decimal
    exists: bool = False


class PrisonerCreate(PrisonerBase):
    judgment_name: Optional[str] = None
    vendor_code: Optional[str] = None
    cases_list: Optional[List[CaseModel]] = []
    search_dir: Optional[str] = None
    case_search_dir: Optional[str] = None
    overpayment: str = None
    refund: Optional[Decimal] = None


class PrisonerModel(BaseModel):
    id: int
    legal_name: str
    amount_paid: Decimal = None
    doc_num: int
    judgment_name: str
    vendor_code: str
    cases_list: Optional[List[CaseModel]] = []
    overpayment: str = None
    refund: Decimal = None
    exists: bool = True

    class Config:
        orm_mode = True

#TODO missing prisoner ORM model