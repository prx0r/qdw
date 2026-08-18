import json

def test_product_passport_genome_outcome_and_portfolio(system,tmp_path):
    idea,_=system.ideas.propose(problem_key="p",solution_key="s",title="Product",summary="summary",
        customer="agents",product_form="app")
    p=system.products.create("Product","product","app",idea_id=idea,factory_id="app",factory_version="1")
    system.products.attach_urls(p,repository_url="https://example.invalid/repo",deployment_url="https://example.invalid")
    system.products.add_genome(p,{"factory":"app","teams":["qa","redteam"]})
    system.products.outcome(p,"api_calls",value=42,source="fixture")
    passport=system.products.passport(p)
    assert passport["idea"]["idea_id"]==idea
    assert passport["factory_genomes"][0]["genome"]["factory"]=="app"
    out=system.portfolio.build(tmp_path/"egoic")
    assert (out/"index.html").exists()
    assert p in (out/"index.html").read_text()

def test_distribution_eligibility(system,tmp_path):
    m={"surface_id":"mcp","name":"MCP","kind":"registry","status":"ACTIVE",
       "product_types":["agent"],"human_account_or_approval_required":True}
    p=tmp_path/"m.json";p.write_text(json.dumps(m))
    system.distributions.register_manifest(p)
    assert system.distributions.eligible("agent")[0]["surface_id"]=="mcp"
