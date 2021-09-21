from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    """
    A class used to track transaction information on a case

    """
    check_number: Optional[str] = None
    amount_paid: Optional[float] = 0.00
