from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,re
from qdw.core.core import hash_object

@dataclass(frozen=True)
class IdeaDossier:
    idea_id:str
    title:str
    problem:str
    solution:str
    customer:str
    product_form:str
    evidence_summary:dict
    score_summary:dict
    risks:tuple[str,...]
    example_domains:tuple[str,...]
    report_hash:str=""

def domain_candidates(title:str,tlds:tuple[str,...]=("com","ai","dev"))->tuple[str,...]:
    stem="".join(re.findall(r"[a-z0-9]+",title.lower()))[:28] or "product"
    return tuple(f"{stem}.{t}" for t in tlds)

def build_dossier(idea:dict,evidence_summary:dict,score_summary:dict,risks:list[str])->IdeaDossier:
    body={
      "idea_id":idea["idea_id"],"title":idea["canonical_title"],"problem":idea["problem_key"],
      "solution":idea["summary"],"customer":idea["customer"],"product_form":idea["product_form"],
      "evidence_summary":evidence_summary,"score_summary":score_summary,"risks":tuple(risks),
      "example_domains":domain_candidates(idea["canonical_title"])
    }
    h=hash_object(body)
    return IdeaDossier(**body,report_hash=h)

def write_dossier(dossier:IdeaDossier,path:str|Path)->Path:
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(asdict(dossier),indent=2),encoding="utf-8")
    return p
