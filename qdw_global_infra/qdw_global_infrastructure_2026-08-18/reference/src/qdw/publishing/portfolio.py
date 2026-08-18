from __future__ import annotations
import html,json
from pathlib import Path
from qdw.core.db import Database

class PortfolioPublisher:
    """Minimal Egoic-like static portfolio. Product Registry remains the source of truth."""

    def __init__(self,db:Database):self.db=db

    def build(self,out_dir:str|Path)->Path:
        out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
        with self.db.connect() as con:
            rows=con.execute("""SELECT * FROM products ORDER BY
                CASE status WHEN 'RELEASED' THEN 0 ELSE 1 END, created_at DESC""").fetchall()
        cards=[]
        for r in rows:
            d=dict(r)
            links=[]
            if d.get("deployment_url"):links.append(f'<a href="{html.escape(d["deployment_url"])}">Live</a>')
            if d.get("repository_url"):links.append(f'<a href="{html.escape(d["repository_url"])}">GitHub</a>')
            cards.append(f"""<article data-product-id="{html.escape(d['product_id'])}">
<h2>{html.escape(d['name'])}</h2><p>{html.escape(d['product_type'])} · {html.escape(d['status'])}</p>
<p>{" · ".join(links)}</p></article>""")
        page="""<!doctype html><html><head><meta charset="utf-8"><title>Egoic Portfolio</title>
<style>body{font-family:system-ui;max-width:900px;margin:3rem auto;padding:0 1rem}article{border-bottom:1px solid #ddd;padding:1rem 0}</style>
</head><body><h1>Products</h1>"""+"\n".join(cards)+"</body></html>"
        (out/"index.html").write_text(page,encoding="utf-8")
        (out/"products.json").write_text(json.dumps([dict(r) for r in rows],indent=2),encoding="utf-8")
        return out
