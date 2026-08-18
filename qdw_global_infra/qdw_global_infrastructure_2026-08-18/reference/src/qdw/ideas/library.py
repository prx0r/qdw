from __future__ import annotations
from qdw.core.db import Database

class IdeaLibrary:
    def __init__(self,db:Database):self.db=db

    def unused(self,limit:int=100)->list[dict]:
        with self.db.connect() as con:
            rows=con.execute("""SELECT * FROM ideas WHERE status IN ('PROPOSED','PASS','DORMANT')
                AND idea_id NOT IN (SELECT idea_id FROM products WHERE idea_id IS NOT NULL)
                ORDER BY updated_at DESC LIMIT ?""",(limit,)).fetchall()
        return [dict(r) for r in rows]

    def same_problem(self,problem_key:str,*,exclude_idea_id:str|None=None)->list[dict]:
        q="SELECT * FROM ideas WHERE problem_key=?";args=[problem_key]
        if exclude_idea_id:q+=" AND idea_id!=?";args.append(exclude_idea_id)
        q+=" ORDER BY created_at"
        with self.db.connect() as con:return [dict(r) for r in con.execute(q,args).fetchall()]

    def inspiration(self,target_form:str,limit:int=20)->list[dict]:
        """Surface unused ideas from other forms; caller may transfer/reimplement them."""
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("""SELECT * FROM ideas
                WHERE product_form!=? AND status IN ('PROPOSED','PASS','DORMANT')
                ORDER BY updated_at DESC LIMIT ?""",(target_form,limit)).fetchall()]
