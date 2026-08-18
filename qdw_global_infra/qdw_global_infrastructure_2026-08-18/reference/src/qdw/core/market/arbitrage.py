from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceLeg:
    amount:float|None
    confidence:float=1.0

@dataclass(frozen=True)
class ArbitrageInputs:
    source_price:PriceLeg
    target_price:PriceLeg
    marketplace_fees:PriceLeg
    payment_fees:PriceLeg
    shipping:PriceLeg
    expected_returns:PriceLeg
    taxes_duties:PriceLeg
    fx_buffer:PriceLeg

@dataclass(frozen=True)
class ArbitrageResult:
    known:bool
    expected_contribution:float|None
    confidence:float
    reason:str

def estimate(i:ArbitrageInputs)->ArbitrageResult:
    legs=[i.source_price,i.target_price,i.marketplace_fees,i.payment_fees,i.shipping,
          i.expected_returns,i.taxes_duties,i.fx_buffer]
    if any(x.amount is None for x in legs):
        return ArbitrageResult(False,None,min(x.confidence for x in legs),"mandatory cost/price unknown")
    contribution=(i.target_price.amount-i.source_price.amount-i.marketplace_fees.amount-i.payment_fees.amount
                  -i.shipping.amount-i.expected_returns.amount-i.taxes_duties.amount-i.fx_buffer.amount)
    return ArbitrageResult(True,contribution,min(x.confidence for x in legs),"complete mandatory inputs")
