def test_forge_profile_becomes_prior_not_qdw_posterior():
    from qdw.federation.candidates import FederatedCandidateCollector
    b=FederatedCandidateCollector().forge([{
       "asset_id":"a","version":"1","status":"ACTIVE","certificate_id":"c",
       "capabilities":["coding"],"pricing":{"per_call":.01},
       "posterior_mean":.9,"sample_count":20,"manifest_hash":"sha256:a"
    }])[0]
    assert b.route.prior_success==.9
    assert b.route.prior_confidence==.4
    assert b.profile["foreign_sample_count"]==20
    # No alpha/beta are copied into QDW route state.
    assert "alpha" not in b.profile and "beta" not in b.profile
