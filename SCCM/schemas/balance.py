from pydantic import BaseModel
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP

cents = Decimal('0.01')


class Balance(BaseModel):
    """
    A class used to track case balance information

    """
    amount_assessed: Optional[Decimal] = 0.00
    amount_collected: Optional[Decimal] = 0.00
    amount_owed: Optional[Decimal] = 0.00

    def update_balance(self) -> None:
        pass

    def add_ccam_balances(self, ccam_balance):
        """
        Add balances from CCAM to case

        :param ccam_balance: CCAM balance

        """
        self.amount_assessed = Decimal(ccam_balance['Total Owed'].item()).quantize(cents,ROUND_HALF_UP)
        self.amount_collected = Decimal(ccam_balance['Total Collected'].item()).quantize(cents,ROUND_HALF_UP)
        self.amount_owed = Decimal(ccam_balance['Total Outstanding'].item()).quantize(cents,ROUND_HALF_UP)

    def mark_paid(self) -> float:
        """
        pay off a case

        :return: overpayment amount
        """
        self.amount_collected = self.amount_assessed
        overpayment = abs(self.amount_owed)
        self.amount_owed = 0
        return overpayment
