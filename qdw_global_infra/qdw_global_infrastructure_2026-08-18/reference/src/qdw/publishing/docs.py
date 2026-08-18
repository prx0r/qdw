from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class DocsPublisher:
    """Produces deterministic project docs from certified registry data, not from an LLM claim."""

    def build(self,passport:dict[str,Any],out_dir:str|Path)->Path:
        out=Path(out_dir);docs=out/"docs";docs.mkdir(parents=True,exist_ok=True)
        p=passport["product"]
        idea=passport.get("idea")
        index=[
            f"# {p['name']}",
            "",
            f"**Type:** {p['product_type']}",
            f"**Status:** {p['status']}",
        ]
        if p.get("domain"):index.append(f"**Domain:** {p['domain']}")
        if p.get("repository_url"):index.append(f"**Repository:** {p['repository_url']}")
        if idea:
            index += ["","## Why it exists",idea["summary"],"",f"Problem key: `{idea['problem_key']}`"]
        index += ["","## Verification",f"Certificate: `{p.get('certificate_id') or 'not-yet-certified'}`",
                  "",f"Factory: `{p.get('factory_id') or 'unknown'}@{p.get('factory_version') or 'unknown'}`"]
        (docs/"index.md").write_text("\n".join(index)+"\n",encoding="utf-8")
        (docs/"passport.json").write_text(json.dumps(passport,indent=2,default=str),encoding="utf-8")
        (out/"mkdocs.yml").write_text(
            f"site_name: {p['name']}\ntheme:\n  name: material\nnav:\n  - Home: index.md\n  - Product Passport: passport.json\n",
            encoding="utf-8")
        return out
