"""Session-isolated local durable store. Development/pilot store; production can implement the same interface."""
from pathlib import Path
import json, datetime, os, tempfile
class LocalStore:
    def __init__(self, root, initiative_id=None, session_id=None):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.initiative_id=initiative_id; self.session_id=session_id; (self.root/'sessions').mkdir(exist_ok=True)
    def now(self): return datetime.datetime.now(datetime.timezone.utc).isoformat()
    @property
    def session_root(self):
        if not self.initiative_id or not self.session_id: raise ValueError('Store is not bound to a session')
        p=self.root/'sessions'/self.initiative_id/self.session_id
        for d in ['artifacts','approvals','questions','logs']: (p/d).mkdir(parents=True,exist_ok=True)
        return p
    def _atomic_text(self,p,content):
        p.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=p.name,dir=p.parent)
        try:
            with os.fdopen(fd,'w') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,p)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _atomic_json(self,p,obj):
        p.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=p.name,dir=p.parent)
        try:
            with os.fdopen(fd,'w') as f: json.dump(obj,f,indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,p)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def save_state(self,s): s['updated_at']=self.now(); self._atomic_json(self.session_root/'state.json',s)
    def load_state(self,*_): return json.loads((self.session_root/'state.json').read_text())
    def save_artifact(self,i,a):
        d=self.session_root/'artifacts'/a['artifact_type']; d.mkdir(parents=True,exist_ok=True); self._atomic_json(d/f'{a["artifact_id"]}__v{a["version"]}.json',a); self._atomic_text(d/f'{a["artifact_id"]}__v{a["version"]}.md',self._markdown(a))
    def _humanize(self,key):
        return str(key).replace('_',' ').strip().title()
    def _render_value(self,value,level=3):
        lines=[]
        if isinstance(value,dict):
            for k,v in value.items():
                title=self._humanize(k)
                if isinstance(v,(dict,list)):
                    lines += [f"{'#'*level} {title}", ''] + self._render_value(v,min(level+1,6)) + ['']
                else:
                    shown='TBD' if v is None else ('Yes' if v is True else 'No' if v is False else str(v))
                    lines += [f"**{title}:** {shown}", '']
        elif isinstance(value,list):
            if not value: return ['_None._']
            for idx,item in enumerate(value,1):
                if isinstance(item,dict):
                    label=item.get('name') or item.get('title') or item.get('id') or f'Item {idx}'
                    lines += [f"{'#'*level} {label}", ''] + self._render_value(item,min(level+1,6)) + ['']
                elif isinstance(item,list):
                    lines += [f'- {x}' for x in item]
                else: lines.append(f'- {item}')
        else: lines.append(str(value))
        return lines
    def _markdown(self,a):
        p=a['payload']; lines=[f"# {p.get('title',a['artifact_type'])}",'',f"**Artifact:** {a['artifact_type']}  ",f"**Version:** {a['version']}  ",f"**Status at generation:** {a['status']}  ",f"**Evidence status:** {p.get('evidence_status','UNKNOWN')}",'','## Executive Summary','',p.get('summary',''),'','## Product Content','']
        lines += self._render_value(p.get('content',{}),3)
        qs=p.get('open_questions',[]); lines += ['','## Open Items','']
        if not qs: lines.append('_None._')
        else:
            groups={}
            for q in qs: groups.setdefault(q.get('classification','UNCLASSIFIED'),[]).append(q)
            labels={'HUMAN_DECISION':'Human Decisions','DISCOVERY_REQUIRED':'Discovery Items','DOWNSTREAM_ANALYSIS':'Downstream Analysis','ASSUMPTION_OR_UNKNOWN':'Assumptions / Unknowns','UNCLASSIFIED':'Unclassified Items'}
            for cls,items in groups.items():
                lines += [f"### {labels.get(cls,self._humanize(cls))}",'']
                for q in items:
                    lines.append(f"- **{q.get('question','')}**")
                    lines.append(f"  - Blocking: {'Yes' if q.get('blocking') else 'No'}")
                    if q.get('owner'): lines.append('  - Owner: '+(', '.join(q['owner']) if isinstance(q['owner'],list) else str(q['owner'])))
                    if q.get('route_to'): lines.append('  - Route to: '+(', '.join(q['route_to']) if isinstance(q['route_to'],list) else str(q['route_to'])))
                    if q.get('resolution_stage'): lines.append('  - Resolution stage: '+str(q['resolution_stage']))
                    if q.get('reason'): lines.append('  - Reason: '+str(q['reason']))
        if p.get('warnings'):
            lines += ['','## Warnings','']+[f'- {x}' for x in p['warnings']]
        return '\n'.join(lines).rstrip()+'\n'
    def render_artifact_markdown(self,i,aid,version):
        a=self.load_artifact(i,aid,version)
        d=self.session_root/'artifacts'/a['artifact_type']; out=d/f'{a["artifact_id"]}__v{a["version"]}.md'; out.write_text(self._markdown(a)); return out
    def load_artifact(self,i,aid,version):
        m=list((self.session_root/'artifacts').glob(f'*/{aid}__v{version}.json'))
        if not m: raise FileNotFoundError(aid)
        return json.loads(m[0].read_text())
    def append_event(self,e):
        with (self.session_root/'events.jsonl').open('a') as f: f.write(json.dumps(e)+'\n')
    def save_resolution(self, artifact_type, blocker_id, record):
        d=self.session_root/'resolutions'/artifact_type
        d.mkdir(parents=True,exist_ok=True)
        self._atomic_json(d/f'{blocker_id}.json',record)
        return d/f'{blocker_id}.json'
    def load_resolution(self, artifact_type, blocker_id):
        p=self.session_root/'resolutions'/artifact_type/f'{blocker_id}.json'
        return json.loads(p.read_text()) if p.exists() else None
    def list_resolutions(self, artifact_type=None):
        root=self.session_root/'resolutions'
        if not root.exists(): return []
        paths=(root/artifact_type).glob('*.json') if artifact_type else root.glob('*/*.json')
        out=[]
        for p in sorted(paths):
            if p.name=='resolution-plan.json': continue
            try: out.append(json.loads(p.read_text()))
            except Exception: continue
        return out
    def save_resolution_plan(self, artifact_type, plan):
        d=self.session_root/'resolutions'/artifact_type
        d.mkdir(parents=True,exist_ok=True)
        self._atomic_json(d/'resolution-plan.json',plan)
        return d/'resolution-plan.json'
    def load_resolution_plan(self, artifact_type):
        p=self.session_root/'resolutions'/artifact_type/'resolution-plan.json'
        return json.loads(p.read_text()) if p.exists() else None
    def append_human_interaction(self, interaction):
        """Append-only business/governance human interaction ledger."""
        with (self.session_root/'human-interactions.jsonl').open('a') as f:
            f.write(json.dumps(interaction, sort_keys=True)+'\n')
        return interaction
    def list_human_interactions(self):
        p=self.session_root/'human-interactions.jsonl'
        if not p.exists(): return []
        out=[]
        for line in p.read_text().splitlines():
            if line.strip():
                try: out.append(json.loads(line))
                except Exception: continue
        return out
    def backfill_human_interactions(self):
        """Idempotently seed the ledger from authoritative historical approvals/clarifications."""
        existing=self.list_human_interactions(); keys={(x.get('source_type'),x.get('source_id')) for x in existing}
        added=0
        for a in self.list_approvals(decision='APPROVED'):
            key=('APPROVAL',a.get('approval_id'))
            if key in keys: continue
            self.append_human_interaction({'schema_version':'1.0','interaction_id':'HI-'+a['approval_id'],'interaction_type':'ARTIFACT_APPROVAL','timestamp':a.get('decided_at'),'actor':a.get('decided_by'),'actor_type':'HUMAN','initiative_id':a.get('initiative_id'),'session_id':a.get('session_id'),'artifact_id':a.get('artifact_id'),'artifact_version':str(a.get('artifact_version')),'approval_id':a.get('approval_id'),'decision':'APPROVED','comments':a.get('comments'),'source_type':'APPROVAL','source_id':a.get('approval_id'),'immutable':True}); added+=1
        try: s=self.load_state()
        except Exception: s={}
        for idx,c in enumerate(s.get('initiative',{}).get('human_clarifications',[]),1):
            sid=c.get('interaction_id') or f"LEGACY-CLARIFICATION-{idx}-{c.get('at','')}"
            key=('CLARIFICATION',sid)
            if key in keys: continue
            self.append_human_interaction({'schema_version':'1.0','interaction_id':sid if str(sid).startswith('HI-') else 'HI-'+str(sid),'interaction_type':'QUESTION_ANSWERED','timestamp':c.get('at'),'actor':c.get('answered_by'),'actor_type':'HUMAN','initiative_id':s.get('initiative_id'),'session_id':s.get('session_id'),'question':c.get('question'),'response':c.get('answer'),'classification':'BUSINESS_REQUIREMENT_INPUT','source_type':'CLARIFICATION','source_id':sid,'immutable':True}); added+=1
        return added
    def save_approval(self,i,a): self._atomic_json(self.session_root/'approvals'/f'{a["approval_id"]}.json',a)
    def list_approvals(self, artifact_id=None, version=None, decision=None):
        out=[]
        for p in sorted((self.session_root/'approvals').glob('*.json')):
            try: a=json.loads(p.read_text())
            except Exception: continue
            if artifact_id is not None and a.get('artifact_id')!=artifact_id: continue
            if version is not None and str(a.get('artifact_version'))!=str(version): continue
            if decision is not None and a.get('decision')!=decision: continue
            out.append(a)
        return out
    def latest_approval(self, artifact_id, version, decision='APPROVED'):
        items=self.list_approvals(artifact_id,version,decision)
        return sorted(items,key=lambda x:x.get('decided_at',''))[-1] if items else None
    def list_sessions(self,initiative_id):
        d=self.root/'sessions'/initiative_id
        if not d.exists(): return []
        out=[]
        for p in sorted(d.iterdir(),reverse=True):
            sf=p/'state.json'
            if sf.exists():
                s=json.loads(sf.read_text()); out.append({'session_id':p.name,'workflow_state':s.get('workflow_state'),'development_context':s.get('initiative',{}).get('development_context'),'updated_at':s.get('updated_at')})
        return out
