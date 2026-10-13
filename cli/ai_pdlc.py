"""AI-PDLC Product Factory v6.1.5 CLI."""
from pathlib import Path
import argparse,sys,yaml,json,os,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime.stores.local import LocalStore
from runtime.orchestrator.product import ProductOrchestrator
from runtime.adapters.mock import MockAdapter
from runtime.adapters.openai_compatible import OpenAICompatibleAdapter
from runtime.adapters.codex import CodexAdapter
RUNTIME=ROOT/'.runtime'
def make_adapter(n): return MockAdapter() if n=='mock' else CodexAdapter() if n=='codex' else OpenAICompatibleAdapter()
def sid(): return 'RUN-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
def store(i=None,s=None): return LocalStore(RUNTIME,i,s)
def runtime(i,s,n):
 st=store(i,s);return st,ProductOrchestrator(ROOT,st,make_adapter(n))
def load_init(p):
 d=yaml.safe_load(Path(p).read_text());i=d.get('initiative',{});req=['initiative_id','title','initiative_type','development_context','problem_or_opportunity','desired_outcome'];miss=[x for x in req if not i.get(x)]
 if miss:raise SystemExit('BLOCKER: missing '+', '.join(miss))
 return d
def show(s):
 print(f'\nInitiative: {s["initiative_id"]}\nSession:    {s["session_id"]}\nState:      {s["workflow_state"]}\nStage:      {s["stage"]}\nAdapter:    {s.get("adapter")}');print(f'Approved:   {sum(1 for x in s["artifacts"].values() if x["status"]=="APPROVED")}/{len(s["required_outputs"])} required outputs')

 if s.get('pending_actions'):
  for action in s['pending_actions']:
   if action.get('type')=='ARTIFACT_REVIEW_REQUIRED': print('ACTION:     ARTIFACT_REVIEW_REQUIRED — '+action.get('artifact_type','')+' v'+action.get('version',''))
   else: print('ACTION:     '+action.get('type','INFORMATION_REQUIRED')+' — '+action.get('question',''))
 elif s['open_questions'] and s['workflow_state']=='PAUSED_WAITING_FOR_HUMAN': print('ACTION:     DECISION_REQUIRED — '+s['open_questions'][0]['question'])
 if s['pending_approvals']:print('REVIEW:     '+s['pending_approvals'][0]['artifact_type']+' v'+s['pending_approvals'][0]['version'])
 active=s.get('active_generation') or {}
 if active.get('artifact_type'): print('CURRENT:    '+str(active.get('artifact_type'))+' | Agent: '+str(active.get('agent_id'))+' | Attempt: '+str(active.get('attempt') or '-'))
 blockers=[x for x in s.get('open_alerts',[]) if x.get('severity')=='BLOCKER' and not x.get('resolved')]
 if blockers:
  b=blockers[-1]; print('BLOCKER:    '+str(b.get('type'))+' | Artifact: '+str(b.get('artifact_type'))+' | Attempt: '+str(b.get('attempt') or '-'))
 rw=s.get('resolution_workflow') or {}
 if rw.get('status')=='ACTIVE': print('BACKWARD:   ACTIVE | Artifact: '+str(rw.get('artifact_type')))
def run_until_pause(st,o,s):
 while s['workflow_state'] in {'READY_TO_RUN','RUNNING'}:
  nxt=o.next_ready(s)
  if not nxt:break
  print(f'\n→ Agent: {o.catalog[nxt]["owner"]} | Generating: {nxt}');a=o.generate_next(s);s=st.load_state()
  if a:print(f'✓ {a["artifact_type"]} v{a["version"]} generated; schema + internal quality review passed.\n⚠ HUMAN REVIEW REQUIRED\n  {st.session_root}/artifacts/{a["artifact_type"]}/')
  if s['workflow_state'] not in {'READY_TO_RUN','RUNNING'}:break
 c=o.completion(s)
 if c['complete']:
  s['workflow_state']='COMPLETED';s['stage']='COMPLETE';st.save_state(s);o.emit(s,'WORKFLOW_COMPLETED','All required outputs approved and final Product Review passed.');print('\n✓ PRODUCT FACTORY SESSION COMPLETE')
 else:show(s)
def run_blocker_resolution(st,o,s,artifact=None,actor='human'):
 result=o.resolve_blockers(s,artifact,actor)
 s=st.load_state()
 status=result.get('status')

 if status=='WAITING_FOR_HUMAN':
  q=result['questions'][0]
  print(f'\n⚠ HUMAN DECISION REQUIRED\nBlocker:    {result["blocker_id"]}\nQuestion:   {q.get("question")}')
  if q.get('recommendation'):print('Recommended: '+str(q.get('recommendation')))
  if q.get('options'):print('Options:    '+json.dumps(q.get('options'),ensure_ascii=False))
  show(s)
  return False

 if status=='BLOCKED':
  print('\n✗ BACKWARD resolution blocked.')
  print('Artifact:     '+str(result.get('artifact_type','UNKNOWN')))
  print('Blocker:      '+str(result.get('blocker_id','UNKNOWN')))
  print('Failure type: '+str(result.get('failure_type','UNKNOWN')))
  print('Reason:       '+str(result.get('message','No details provided')))
  show(s)
  return False

 if status!='RESOLVED':
  print('\n✗ Unexpected blocker-resolution status: '+str(status))
  show(s)
  return False

 print(f'✓ BACKWARD resolution complete for {result["artifact_type"]}: {len(result.get("resolution_refs",[]))} blocker(s) resolved.')
 print('→ Returning automatically to governed artifact regeneration and Product Definition review...')
 run_until_pause(st,o,st.load_state())
 return True

def resolve(i,s):
 if s:return s
 ss=store().list_sessions(i)
 if len(ss)==1:return ss[0]['session_id']
 if not ss:raise SystemExit('No sessions found')
 raise SystemExit('Multiple sessions exist. Specify --session <RUN-id>.')
ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='area');p=sp.add_parser('product');ps=p.add_subparsers(dest='cmd')
x=ps.add_parser('start');x.add_argument('initiative');x.add_argument('--adapter',choices=['model','mock','codex'],default='codex');x.add_argument('--session')
for cmd in ['continue','resume','status']:
 x=ps.add_parser(cmd);x.add_argument('initiative_id');x.add_argument('--session')
 if cmd in ['continue','resume']:x.add_argument('--adapter',choices=['model','mock','codex'])
x=ps.add_parser('sessions');x.add_argument('initiative_id')
for cmd in ['approve','changes','reject','answer']:
 x=ps.add_parser(cmd);x.add_argument('initiative_id');x.add_argument('--session');x.add_argument('--actor',default=os.getenv('USER','human'))
 if cmd=='approve':x.add_argument('--comments')
 elif cmd in ['changes','reject']:x.add_argument('comments')
 else:x.add_argument('answer')
x=ps.add_parser('artifact');x.add_argument('initiative_id');x.add_argument('artifact_type');x.add_argument('--session')
x=ps.add_parser('render');x.add_argument('initiative_id');x.add_argument('artifact_type');x.add_argument('--session')
x=ps.add_parser('retry');x.add_argument('initiative_id');x.add_argument('--session');x.add_argument('--actor',default=os.getenv('USER','human'));x.add_argument('--reason',default='Retry after runtime/context correction')
x=ps.add_parser('resolve-blockers');x.add_argument('initiative_id');x.add_argument('--session');x.add_argument('--artifact');x.add_argument('--actor',default=os.getenv('USER','human'))
x=ps.add_parser('input');x.add_argument('initiative_id');x.add_argument('text');x.add_argument('--type',dest='interaction_type',default='BUSINESS_REQUIREMENT_INPUT');x.add_argument('--classification');x.add_argument('--supersedes');x.add_argument('--session');x.add_argument('--actor',default=os.getenv('USER','human'))
x=ps.add_parser('audit');x.add_argument('initiative_id');x.add_argument('--session')
x=ps.add_parser('audit-backfill');x.add_argument('initiative_id');x.add_argument('--session')
a=ap.parse_args()
if a.area!='product':ap.print_help();sys.exit(1)
if a.cmd=='sessions':
 for z in store().list_sessions(a.initiative_id):print(f'{z["session_id"]} | {z["workflow_state"]} | {z["development_context"]} | {z["updated_at"]}')
 sys.exit()
if a.cmd=='start':
 d=load_init(a.initiative);i=d['initiative']['initiative_id'];s_id=a.session or sid();st,o=runtime(i,s_id,a.adapter);s=o.start(d,s_id,a.adapter);print(f'\n✓ Session created: {s_id}\nWorkspace: {st.session_root}\nAdapter: {a.adapter}');run_until_pause(st,o,s);sys.exit()
i=a.initiative_id;s_id=resolve(i,getattr(a,'session',None));st=store(i,s_id);s=st.load_state()
if a.cmd=='status':show(s);sys.exit()
if a.cmd=='audit':
 for z in st.list_human_interactions(): print(json.dumps(z,indent=2))
 sys.exit()
if a.cmd=='audit-backfill':
 n=st.backfill_human_interactions();print(f'✓ Human interaction audit backfill complete: {n} record(s) added.');sys.exit()
if a.cmd=='input':
 n=s.get('adapter','codex');st,o=runtime(i,s_id,n);r=o.record_human_input(s,a.text,a.interaction_type,a.actor,a.classification,a.supersedes);print(f'✓ Human input recorded at {r["timestamp"]} | {r["interaction_id"]}');sys.exit()

if a.cmd=='artifact':
 m=s['artifacts'].get(a.artifact_type)
 if not m:raise SystemExit('Artifact not found')
 print(json.dumps(st.load_artifact(i,m['artifact_id'],m['version']),indent=2));sys.exit()
if a.cmd=='render':
 m=s['artifacts'].get(a.artifact_type)
 if not m:raise SystemExit('Artifact not found')
 out=st.render_artifact_markdown(i,m['artifact_id'],m['version']);print(f'✓ Human-readable Markdown rendered: {out}');sys.exit()
if a.cmd=='resolve-blockers':
 n=s.get('adapter','codex');st,o=runtime(i,s_id,n);run_blocker_resolution(st,o,s,a.artifact,a.actor);sys.exit()
if a.cmd=='retry':
 n=s.get('adapter','codex');st,o=runtime(i,s_id,n);result=o.retry_pending_generation(s,a.actor,a.reason);print(f'✓ Retry prepared for {result.get("artifact_type") or "blocked generation"} from {result.get("previous_stage")}. Cleared {len(result.get("cleared_questions",[]))} question(s).');run_until_pause(st,o,st.load_state());sys.exit()
if a.cmd in {'continue','resume'}:
 n=a.adapter or s.get('adapter','codex');st,o=runtime(i,s_id,n)
 if s['workflow_state'] not in {'READY_TO_RUN','RUNNING','REWORK'}:raise SystemExit('Workflow is waiting for human action; resolve it first.')
 s['workflow_state']='READY_TO_RUN';st.save_state(s);run_until_pause(st,o,s);sys.exit()
if a.cmd in {'approve','changes','reject'}:
 n=s.get('adapter','codex');st,o=runtime(i,s_id,n);d={'approve':'APPROVED','changes':'CHANGES_REQUESTED','reject':'REJECTED'}[a.cmd];o.decide(s,d,getattr(a,'comments',None),a.actor);print(f'✓ {d}. Automatically continuing session {s_id}...');run_until_pause(st,o,st.load_state());sys.exit()
if a.cmd=='answer':
 n=s.get('adapter','codex');st,o=runtime(i,s_id,n);o.answer(s,a.answer,a.actor);print('✓ Answer recorded. Automatically continuing...');s2=st.load_state();rw=s2.get('resolution_workflow') or {}
 if rw.get('status')=='ACTIVE':run_blocker_resolution(st,o,s2,None,a.actor)
 else:run_until_pause(st,o,s2)
 sys.exit()
p.print_help()
