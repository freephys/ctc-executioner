import copy
from order_side import OrderSide
from order_type import OrderType
from match_engine import MatchEngine
import numpy as np

class Action(object):

    def __init__(self, a, runtime):
        self.a = a
        self.runtime = runtime
        self.order = None
        self.trades = []  # filled order
        self.orderbookState = None
        self.orderbookIndex = None

    def getA(self):
        return self.a

    def getRuntime(self):
        return self.runtime

    def setRuntime(self, runtime):
        self.runtime = runtime

    def setOrderbookState(self, state):
        self.orderbookState = state

    def getOrderbookState(self):
        return self.orderbookState

    def setOrderbookIndex(self, index):
        self.orderbookIndex = index

    def getOrderbookIndex(self):
        return self.orderbookIndex

    def getOrder(self):
        return self.order

    def setOrder(self, order):
        self.order = order

    def getTrades(self):
        return self.trades

    def setTrades(self, trades):
        self.trades = trades

    def getAvgPrice(self):
        """Returns the average price paid for the executed order."""
        if self.getQtyExecuted() == 0:
            return 0.0

        price = 0.0
        for trade in self.getTrades():
            price = price + trade.getCty() * trade.getPrice()
        return price / self.getQtyExecuted()

    def getQtyExecuted(self):
        qty = 0.0
        for trade in self.getTrades():
            qty = qty + trade.getCty()
        return qty

    def getQtyNotExecuted(self):
        return self.getOrder().getCty() - self.getQtyExecuted()

    def isFilled(self):
        return self.getQtyExecuted() == self.order.getCty()

    def getTotalPaidReceived(self):
        return self.getAvgPrice() * self.getQtyExecuted()

    def getValueAbs(self):
        """Retuns difference of the paid amount to the total bid/ask-mid amount.
        The higher, the better,
        For BUY: total paid at mid price - total paid
        For SELL: total received - total received at mid price
        """
        midPrice = self.getOrderbookState().getBidAskMid()

        # In case of no executed trade, the value is the negative reference
        if self.getTotalPaidReceived() == 0.0:
            return -midPrice

        if self.getOrder().getSide() == OrderSide.BUY:
            return midPrice - self.getTotalPaidReceived()
        else:
            return self.getTotalPaidReceived() - midPrice

    def getValueAvg(self):
        """Retuns difference of the average paid price to bid/ask-mid price.
        The higher, the better,
        For BUY: total paid at mid price - total paid
        For SELL: total received - total received at mid price
        """
        # In case of no executed trade, the value is the negative reference
        if self.getPcFilled() == 0.0:
            return 0.0 # -2.0 * abs(self.getA())

        midPrice = self.getOrderbookState().getBidAskMid()
        if self.getOrder().getSide() == OrderSide.BUY:
            return midPrice - self.getAvgPrice()
        else:
            return self.getAvgPrice() - midPrice

    def getTestReward(self):
        if self.getA() == 1:
            return 100.0
        else:
            return -100.0

    def getPcFilled(self):
        return 10 * (self.getQtyExecuted() / self.getOrder().getCty())

    def getValueExecuted(self):
        r = 10.0
        if self.getA() > 0:
            r = -r

        return self.getPcFilled() + r * np.log(1.0 + abs(self.getA()))

    def update(self, a, runtime):
        """Updates an action to be ready for the next run."""
        if runtime <= 0.0:
            price = None
            self.getOrder().setType(OrderType.MARKET)
        else:
            price = self.getOrderbookState().getPriceAtLevel(self.getOrder().getSide(), a)

        self.getOrder().setPrice(price)
        self.getOrder().setCty(self.getQtyNotExecuted())
        self.setRuntime(runtime)
        return self

    def run(self, orderbook):
        """Runs action using match engine.
        The orderbook is provided and being used in the match engine along with
        the prviously determined index where the action should start matching.
        The matching process returns the trades and the remaining quantity
        along with the index the matching stopped.
        The action gets updated with those values accordingly such that it can
        be evaluated or run over again (e.g. with a new runtime).
        """
        matchEngine = MatchEngine(orderbook, index=self.getOrderbookIndex())
        counterTrades, qtyRemain, index = matchEngine.matchOrder(self.getOrder(), self.getRuntime())
        self.setTrades(counterTrades)
        self.setOrderbookIndex(index=index)
        self.setOrderbookState(orderbook.getState(index))
        return self, qtyRemain