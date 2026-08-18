import pytest
from qdw_finishline.forge import BudgetError

def test_exact_estimate_settles(forge):
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.02,operations=("invoke",))
    x=forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")
    assert x.cost==.01 and forge.leases[l["lease_id"]].spend==.01

def test_lower_actual_refunds_reservation(forge):
    forge.actual_cost_overrides[("api.builder","1.0.0")]=.004
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.02,operations=("invoke",))
    x=forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")
    assert x.cost==.004 and forge.leases[l["lease_id"]].spend==.004

def test_higher_actual_settles_when_budget_allows(forge):
    forge.actual_cost_overrides[("api.builder","1.0.0")]=.015
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.02,operations=("invoke",))
    x=forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")
    assert x.cost==.015 and forge.leases[l["lease_id"]].spend==.015

def test_estimate_over_budget_rejected(forge):
    with pytest.raises(BudgetError):
        l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                             calls=1,max_spend=.005,operations=("invoke",))
        forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")

def test_actual_over_budget_fails_without_claiming_success(forge):
    forge.actual_cost_overrides[("api.builder","1.0.0")]=.03
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.02,operations=("invoke",))
    x=forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")
    assert x.status=="FAILED"
