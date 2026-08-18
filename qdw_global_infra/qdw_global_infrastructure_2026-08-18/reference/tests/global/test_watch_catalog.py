def test_watch_trigger_does_not_mutate_subject(system):
    idea,_=system.ideas.propose(problem_key="tts cost",solution_key="x",title="Old idea",
        summary="x",customer="agents",product_form="api")
    system.ideas.bury(idea,"TOO_EXPENSIVE",assumptions={"cost":10},revisit_triggers=[{"cost_below":1}])
    t=system.watch.add("idea",idea,"resource_change",{"capability":"tts","cost_below":1})
    hits=system.watch.due_for_signal({"capability":"tts","cost_below":1})
    assert hits[0]["trigger_id"]==t
    # watch only recommends re-evaluation; it cannot silently revive.
    assert system.ideas.cemetery()[0]["status"]=="DORMANT"

def test_global_catalog_reads_same_database(system):
    system.world.upsert_entity("provider","Provider X",external_key="px")
    idea,_=system.ideas.propose(problem_key="p",solution_key="s",title="Provider Helper",
        summary="summary",customer="devs",product_form="api")
    result=system.catalog.search("provider")
    assert result["entities"] and result["ideas"]
