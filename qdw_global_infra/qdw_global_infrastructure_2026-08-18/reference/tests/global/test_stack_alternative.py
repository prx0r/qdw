def test_stack_oracle_hard_unknown_constraint(system):
    system.stack.ensure_capability("tts","Text to speech","audio")
    a=system.stack.register_resource("tts","Known",resource_key="known",provider="P")
    b=system.stack.register_resource("tts","Unknown cost",resource_key="unknown",provider="P")
    system.stack.measure(a,"quality",value=.9)
    system.stack.measure(a,"cost",value=.01)
    system.stack.measure(b,"quality",value=.99)
    recs=system.stack.recommend("tts",max_cost=.02,min_quality=.8)
    assert [r.resource_id for r in recs]==[a]

def test_alternative_gap_becomes_opportunity(system):
    system.stack.ensure_capability("ocr-khmer","Khmer OCR","ocr")
    result=system.alternatives.match("ocr-khmer",max_cost=.001,min_quality=.95,create_gap=True)
    assert result.build_gap is True
    assert result.opportunity_id
    opp=system.opportunities.get(result.opportunity_id)
    assert opp["kind"]=="api_gap"
    assert opp["factory_hint"]=="api"
