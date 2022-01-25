from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

from SCCM.models.case_schema import CaseBase
import SCCM.models.transaction_schema as ts
from SCCM.models.prisoner_schema import PrisonerCreate
import SCCM.services.payment_services as payment

cents = Decimal('0.01')


class Context:
    """
    The Context defines the interface of interest to clients.
    """

    def __init__(self, strategy: Strategy) -> None:
        """
        Usually, the Context accepts a strategy through the constructor, but
        also provides a setter to change it at runtime.
        """

        self._strategy = strategy

    @property
    def strategy(self) -> Strategy:
        """
        The Context maintains a reference to one of the Strategy objects. The
        Context does not know the concrete class of a strategy. It should work
        with all strategies via the Strategy interface.
        """

        return self._strategy

    @strategy.setter
    def strategy(self, strategy: Strategy) -> None:
        """
        Usually, the Context allows replacing a Strategy object at runtime.
        """

        self._strategy = strategy

    def process_payment(self, p: PrisonerCreate, check_number: int) -> None:
        result = self._strategy.process_payment(p, check_number)


class Strategy(ABC):
    """
       The Strategy interface declares operations common to all supported versions
       of some algorithm.

       The Context uses this interface to call the algorithm defined by Concrete
       Strategies.
    """

    @abstractmethod
    def process_payment(self, p: PrisonerCreate, check_number: int):
        pass


class SingleCasePaymentProcess(Strategy):
    def process_payment(self, p: PrisonerCreate, check_number: int) -> Prisoners:
        case = p.cases_list[0]
        overpayment = False
        case.balance.amount_collected = Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP) \
                                        + p.amount_paid
        case.balance.amount_owed = Decimal(case.balance.amount_assessed).quantize(cents, ROUND_HALF_UP) \
                                   - Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP)
        if case.balance.amount_owed < 0:
            overpayment = True
        if overpayment:
            payment.prepare_overpayment(p, case, check_number)
        else:
            payment.prepare_payment(p, case, check_number)
        return p


class MultipleCasePaymentProcess(Strategy):
    """
    Class that handles applying payments to multiple cases
    """

    def process_payment(self, p: PrisonerCreate, check_number: int) -> Prisoners:
        number_of_cases_for_prisoner = len(p.cases_list)
        overpayment = False
        all_payments_applied = False

        while not all_payments_applied and number_of_cases_for_prisoner > 0:
            for case in p.cases_list:
                case.balance.amount_collected = Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP) \
                                                + p.amount_paid
                case.balance.amount_owed = Decimal(case.balance.amount_assessed).quantize(cents, ROUND_HALF_UP) \
                                           - Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP)

                if case.balance.amount_owed < 0:
                    overpayment = True
                else:
                    # When applying payments to successive cases, if no overpayment exists, we need to clear the overpayment
                    # flag to allow for the loop to break and delete the overpayment set in the previous to loop to
                    # avoid adding an overpayment line to the CCAM upload file
                    overpayment = False
                    p.overpayment = None

                if overpayment:
                    payment.prepare_overpayment(p, case, check_number)
                    number_of_cases_for_prisoner -= 1
                else:
                    payment.prepare_payment(p, case, check_number)
                    all_payments_applied = True
                    p.refund = 0
                    break
        return p


class OverPaymentProcess(Strategy):
    """
    Class that applies and overpayment when a prisoner has no cases found
    """

    def process_payment(self, p: PrisonerCreate, check_number: int) -> Prisoners:
        p.refund = p.amount_paid
        p.overpayment = {'overpayment': True,
                         'ccam_case_num': 'No Active Cases',
                         'assessed': 0,
                         'collected': 0,
                         'outstanding': 0,
                         'transaction amount': -p.refund
                         }
        return p
