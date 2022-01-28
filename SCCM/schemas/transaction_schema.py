from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class TransactionBase(BaseModel):
    check_number: int
    amount_paid: Decimal


class TransactionCreate(TransactionBase):
    pass


class TransactionModel(TransactionBase):
    id: int
    created_date: datetime
    amount_paid: Decimal

    class Config:
        orm_mode = True
