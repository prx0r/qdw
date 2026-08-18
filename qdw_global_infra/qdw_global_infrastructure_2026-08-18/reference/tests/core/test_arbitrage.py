from qdw.core.market.arbitrage import PriceLeg,ArbitrageInputs,estimate
def test_unknown_blocks_claim():
    z=PriceLeg(0)
    i=ArbitrageInputs(PriceLeg(10),PriceLeg(20),z,z,z,z,PriceLeg(None),z)
    r=estimate(i)
    assert not r.known and r.expected_contribution is None
def test_complete_margin():
    z=PriceLeg(0)
    i=ArbitrageInputs(PriceLeg(10),PriceLeg(20),PriceLeg(1),z,PriceLeg(2),z,z,z)
    assert estimate(i).expected_contribution==7
