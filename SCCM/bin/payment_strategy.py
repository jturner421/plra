from __future__ import annotations
from typing import List
from abc import ABC, abstractmethod
from SCCM.bin.case import Case


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

    def process_payment(self, case, amount_paid) -> None:
        result = self._strategy.process_payment(case, amount_paid)
        pass


class Strategy(ABC):
    """
       The Strategy interface declares operations common to all supported versions
       of some algorithm.

       The Context uses this interface to call the algorithm defined by Concrete
       Strategies.
    """

    @abstractmethod
    def process_payment(self, case: Case, amount_paid: float):
        pass


class SingleCasePaymentProcess(Strategy):
    def process_payment(self, case: Case, amount_paid: float) -> Case:
        pass


class MultipleCasePaymentProcess(Strategy):
    def process_payment(self, case: Case, amount_paid: float) -> Case:

        case.balance.amount_collected = case.balance.amount_collected + amount_paid
        case.balance.amount_owed = case.balance.amount_assessed - case.balance.amount_collected
        if case.balance.amount_owed < 0:
            case.overpayment = True
        return case


class OverPaymentProcess(Strategy):
    def process_payment(self, case: Case,amount_paid: float) -> Case:
        pass
