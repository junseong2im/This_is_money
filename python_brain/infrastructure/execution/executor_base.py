from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    """
    Execution layer interface.
    This layer MUST NOT contain any strategy logic.
    """

    @abstractmethod
    def execute(
        self,
        decision: dict,
        price: float,
        funding_rate: float
    ):
        """
        Execute a trading decision.

        decision: output from core.engine
        price: current market price
        funding_rate: current funding rate
        """
        pass
