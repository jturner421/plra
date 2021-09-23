from dataclasses import dataclass
from typing import Optional, SupportsAbs


@dataclass
class Balance:
    """
    A class used to track case balance information

    """
    amount_assessed: Optional[float] = 0
    amount_collected: Optional[float] = 0
    amount_owed: SupportsAbs[SupportsAbs[float]] = 0

    def update_balance(self) -> None:
        pass

    def add_ccam_balances(self, ccam_balance):
        """
        Add balances from CCAM to case

        :param ccam_balance: CCAM balance

        """
        self.amount_assessed = ccam_balance['Total Owed']
        self.amount_collected = ccam_balance['Total Collected']
        self.amount_owed = ccam_balance['Total Outstanding']

    def mark_paid(self) -> SupportsAbs[float]:
        """
        pay off a case

        :return: overpayment amount
        """
        self.amount_collected = self.amount_assessed
        overpayment: SupportsAbs[float] = abs(self.amount_owed)
        self.amount_owed = 0
        return overpayment
