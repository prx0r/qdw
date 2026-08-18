from qdw.sources.protocol import SourceResult

def _obs(system,source,family,text):
    return system.world.record_source_result(
        SourceResult.success(source,family,[{"id":source,"text":text}])
    )[0]

def test_pain_cluster_aggregates_independent_sources(system):
    text="Exporting invoice reconciliation reports every week is tedious and expensive"
    o1=_obs(system,"hn","forum",text)
    o2=_obs(system,"issues","github_issue",text)
    _,c1=system.pain.ingest(o1,text,intensity=.8,recurrence_hint=.9,machine_solvable=.9,verifiable=.8)
    _,c2=system.pain.ingest(o2,text,intensity=.7,recurrence_hint=.8,machine_solvable=.9,verifiable=.9)
    assert c1==c2
    c=system.pain.cluster(c1)
    assert c["mention_count"]==2
    assert c["source_family_count"]==2
    assert c["confidence"]>0

def test_pain_top_returns_scored_clusters(system):
    o=_obs(system,"a","forum","Syncing API invoices into accounting software is annoying")
    system.pain.ingest(o,"Syncing API invoices into accounting software is annoying",
                       intensity=.9,recurrence_hint=.9,machine_solvable=.9,verifiable=.9)
    assert system.pain.top(1)[0]["mention_count"]==1
