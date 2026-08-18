from __future__ import annotations
import json
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path

class ReviewerCatalog:
    def __init__(self,manifest_dir:str|Path,prompt_dir:str|Path,*,db=None,active_only:bool=False):
        self.manifest_dir=Path(manifest_dir)
        self.prompt_dir=Path(prompt_dir)
        self.db=db
        self.active_only=active_only

    def definitions(self,include_inactive:bool=False)->list[dict]:
        out=[]
        statuses={}
        if self.db is not None:
            with self.db.connect() as con:
                statuses={
                    (r["contractor_id"],r["version"]):r["status"]
                    for r in con.execute("""SELECT contractor_id,version,status FROM contractor_definitions
                        WHERE contractor_id LIKE 'review.%'""").fetchall()
                }
        for path in sorted(self.manifest_dir.glob("review.*.json")):
            manifest=json.loads(path.read_text(encoding="utf-8"))
            # Normalize key: some manifests use reviewer_id, others contractor_id
            if "contractor_id" not in manifest and "reviewer_id" in manifest:
                manifest["contractor_id"] = manifest["reviewer_id"]
            manifest["definition_hash"]=sha256(
                json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
            ).hexdigest()
            manifest["registry_status"]=statuses.get(
                (manifest["contractor_id"],manifest["version"]),"UNREGISTERED"
            )
            if self.active_only and not include_inactive and manifest["registry_status"]!="ACTIVE":
                continue
            out.append(manifest)
        return out

    def select(self,changed_paths:tuple[str,...],profile:str)->list[dict]:
        defs=self.definitions()
        if profile in {"full","release","self-review"}:
            return [x for x in defs if x.get("enabled",True)]
        selected=[]
        for definition in defs:
            patterns=definition.get("path_patterns",["**"])
            if definition.get("always") or any(
                fnmatch(path,pattern)
                for path in changed_paths
                for pattern in patterns
            ):
                selected.append(definition)
        return selected

    def prompt(self,definition:dict)->str:
        name=definition.get("prompt_file") or (definition["contractor_id"]+".md")
        return (self.prompt_dir/name).read_text(encoding="utf-8")
