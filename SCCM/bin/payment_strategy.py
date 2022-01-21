from __future__ import annotations
from abc import ABC, abstractmethod
from SCCM.models.case import CaseBase
from SCCM.bin.transaction import Transaction
from SCCM.bin.prisoners import Prisoners
from decimal import Decimal, ROUND_HALF_UP

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

    def process_payment(self, p: Prisoners, check_number: int) -> None:
        result = self._strategy.process_payment(p, check_number)


class Strategy(ABC):
    """
       The Strategy interface declares operations common to all supported versions
       of some algorithm.

       The Context uses this interface to call the algorithm defined by Concrete
       Strategies.
    """

    @abstractmethod
    def process_payment(self, p: Prisoners, check_number: int):
        pass


class SingleCasePaymentProcess(Strategy):
    def process_payment(self, p: Prisoners, check_number: int) -> Prisoners:
        case = p.cases_list[0]
        overpayment = False
        case.balance.amount_collected = Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP) \
                                        + p.amount_paid
        case.balance.amount_owed = Decimal(case.balance.amount_assessed).quantize(cents, ROUND_HALF_UP) \
                                   - Decimal(case.balance.amount_collected).quantize(cents, ROUND_HALF_UP)
        if case.balance.amount_owed < 0:
            overpayment = True
        if overpayment:
            case.status = 'PAID'
            overpayment = case.balance.mark_paid()
            case.transaction = Transaction(check_number, p.amount_paid - Decimal(overpayment).
                                           quantize(cents, ROUND_HALF_UP))
            p.refund = overpayment
        else:
            case.transaction = Transaction(check_number, p.amount_paid)
        return p


class MultipleCasePaymentProcess(Strategy):
    def process_payment(self, p: Prisoners, check_number: int) -> Prisoners:
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
                    overpayment = False

                if overpayment:
                    case.status = 'PAID'
                    overpayment = case.balance.mark_paid()
                    case.transaction = Transaction(check_number, p.amount_paid - Decimal(overpayment).
                                                   quantize(cents, ROUND_HALF_UP))
                    p.amount_paid = overpayment
                    p.refund = overpayment
                    number_of_cases_for_prisoner -= 1
                else:
                    case.transaction = Transaction(check_number, p.amount_paid)
                    all_payments_applied = True
                    p.refund = 0
                    break
        return p


class OverPaymentProcess(Strategy):
    def process_payment(self, p: Prisoners, check_number: int) -> Prisoners:
        # p.cases_list.append(CaseBase('No Active Cases', 'PAID', True))
        p.overpayment = True
        p.refund = p.amount_paid
        return p
