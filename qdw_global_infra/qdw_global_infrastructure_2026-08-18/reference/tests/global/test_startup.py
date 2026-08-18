def test_startup_events_share_world_entities(system):
    e=system.startups.record_company_event("ExampleCo","funded","2026-08-01T00:00:00Z",
        external_key="exampleco",amount_usd=1000000,stage="seed",attributes={"category":"developer_tools"})
    rows=system.startups.recent()
    assert rows[0]["startup_event_id"]==e
    assert rows[0]["company_name"]=="ExampleCo"
    assert system.startups.category_counts()["developer_tools"]==1
