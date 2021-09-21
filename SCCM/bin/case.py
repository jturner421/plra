import os
from collections import Counter
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
import fuzz as fuzz
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from SCCM.bin.balance import Balance


@dataclass
class Case:
    """
    A class used to track case information

    """
    case_number: str
    status: str
    balance: Optional[Balance] = None
    case_search_dir: Optional[str] = None
    formatted_case_num: Optional[str] = None
    acct_cd: Optional[str] = None

