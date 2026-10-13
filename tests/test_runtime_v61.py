from pathlib import Path
import sys,tempfile,yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime.stores.local import LocalStore
from runtime.adapters.mock import MockAdapter
from runtime.orchestrator.product import ProductOrchestrator
def setup(d,name='consumer-event-planner.yaml',sid='RUN-TEST'):
 init=yaml.safe_load((ROOT/'intake/examples'/name).read_text());i=init['initiative']['initiative_id'];st=LocalStore(d,i,sid);o=ProductOrchestrator(ROOT,st,MockAdapter());return init,st,o
def test_session_and_rework():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);a=o.generate_next(o.start(init,'RUN-TEST','mock'));assert a['artifact_type']=='PRODUCT_CHARTER';o.decide(st.load_state(),'CHANGES_REQUESTED','Make scope clearer','tester');s=st.load_state();assert s['rework_feedback']['PRODUCT_CHARTER']['comments']=='Make scope clearer';a2=o.generate_next(s);assert a2['version']=='2';o.decide(st.load_state(),'APPROVED',actor='tester');assert st.load_state()['workflow_state']=='READY_TO_RUN'
def test_isolation():
 with tempfile.TemporaryDirectory() as d:
  for sid in ['RUN-A','RUN-B']:
   init,st,o=setup(d,sid=sid);o.generate_next(o.start(init,sid,'mock'))
  i=init['initiative']['initiative_id'];assert (Path(d)/'sessions'/i/'RUN-A'/'state.json').exists();assert (Path(d)/'sessions'/i/'RUN-B'/'state.json').exists()
def test_full_creation_completion():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);s=o.start(init,'RUN-TEST','mock');guard=0
  while not o.completion(s)['complete']:
   guard+=1;assert guard<80
   if s['pending_approvals']:o.decide(s,'APPROVED',actor='tester');s=st.load_state();continue
   a=o.generate_next(s);assert a is not None;s=st.load_state()
  assert s['final_product_review_passed'];assert len(s['required_outputs'])==24

def test_v612_markdown_is_human_readable():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);a=o.generate_next(o.start(init,'RUN-TEST','mock')); md=(st.session_root/'artifacts'/'PRODUCT_CHARTER'/f'{a["artifact_id"]}__v{a["version"]}.md').read_text()
  assert '```json' not in md
  assert '## Product Content' in md
  assert '## Open Items' in md

def test_v612_question_classification_and_actions():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);s=o.start(init,'RUN-TEST','mock')
  p={'open_questions':[{'question':'Choose release scope','blocking':True},{'question':'Research user workflow','blocking':False,'classification':'DISCOVERY_REQUIRED'}]}
  o._classify_questions(p)
  assert p['open_questions'][0]['classification']=='HUMAN_DECISION'
  assert p['open_questions'][1]['blocking'] is False

def test_v612_schema_failure_never_references_unbound_review():
 class BadAdapter:
  def generate(self,system,user): return {'artifact_type':'WRONG'}
 with tempfile.TemporaryDirectory() as d:
  init=yaml.safe_load((ROOT/'intake/examples/consumer-event-planner.yaml').read_text()); i=init['initiative']['initiative_id']; st=LocalStore(d,i,'RUN-BAD'); o=ProductOrchestrator(ROOT,st,BadAdapter()); s=o.start(init,'RUN-BAD','bad'); a=o.generate_next(s); assert a is None; s=st.load_state(); assert s['stage']=='SCHEMA_VALIDATION_FAILED'


def test_v613_approval_context_propagates_and_no_duplicate_approval_question():
 class SpyAdapter:
  def __init__(self): self.users=[]
  def generate(self,system,user):
   self.users.append(user)
   typ=user.split('OUTPUT_TYPE: ',1)[1].split('\n',1)[0] if 'OUTPUT_TYPE: ' in user else 'REVIEW'
   if 'Independently review this ' in user: return {'pass':True,'findings':[]}
   return {'artifact_type':typ,'title':typ,'summary':'ok','content':{},'evidence_status':'UNKNOWN','open_questions':[],'warnings':[],'traceability':[],'affected_outputs':[]}
 with tempfile.TemporaryDirectory() as d:
  init=yaml.safe_load((ROOT/'intake/examples/consumer-event-planner.yaml').read_text());i=init['initiative']['initiative_id'];st=LocalStore(d,i,'RUN-V613');ad=SpyAdapter();o=ProductOrchestrator(ROOT,st,ad);s=o.start(init,'RUN-V613','spy');a=o.generate_next(s);o.decide(st.load_state(),'APPROVED',actor='Gabi Angina');s=st.load_state();o.generate_next(s)
  brief_prompts=[u for u in ad.users if u.startswith('OUTPUT_TYPE: PRODUCT_BRIEF')];assert brief_prompts
  u=brief_prompts[-1];assert '"status": "APPROVED"' in u;assert '"approval_id":' in u;assert '"approved_by": "Gabi Angina"' in u;assert 'never ask the human to reconfirm' in u

def test_v613_prior_revision_propagates_on_rework():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);a=o.generate_next(o.start(init,'RUN-TEST','mock'));o.decide(st.load_state(),'CHANGES_REQUESTED','Revise it','tester');s=st.load_state();prior=o._prior_revision(s,'PRODUCT_CHARTER');assert prior and prior['version']=='1';prompt=o._prompt(s,'PRODUCT_CHARTER',[],[],prior);assert 'PRIOR_REVISION_FOR_REWORK' in prompt;assert 'Revise it' in prompt

def test_v613_retry_clears_stale_information_request():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);s=o.start(init,'RUN-TEST','mock');s['workflow_state']='PAUSED_WAITING_FOR_HUMAN';s['stage']='INFORMATION_REQUIRED';s['open_questions']=[{'question':'reapprove?','blocking':True,'classification':'HUMAN_DECISION'}];s['pending_actions']=[{'type':'DECISION_REQUIRED','question':'reapprove?','blocking':True}];st.save_state(s);cleared=o.retry_pending_generation(st.load_state(),'tester','approval context fixed');s=st.load_state();assert len(cleared['cleared_questions'])==1;assert s['workflow_state']=='READY_TO_RUN';assert not s['open_questions'];assert not s['pending_actions']


def test_v614_human_approval_and_answer_audit():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);a=o.generate_next(o.start(init,'RUN-TEST','mock'));o.decide(st.load_state(),'APPROVED',actor='tester');items=st.list_human_interactions();assert any(x['interaction_type']=='ARTIFACT_APPROVAL' and x.get('timestamp') for x in items)
  s=st.load_state();s['workflow_state']='PAUSED_WAITING_FOR_HUMAN';s['stage']='HUMAN_DECISION_REQUIRED';s['open_questions']=[{'question_id':'Q-1','question':'What scope?','blocking':True,'classification':'HUMAN_DECISION','asked_at':st.now()}];st.save_state(s);o.answer(st.load_state(),'Small events','tester');items=st.list_human_interactions();ans=[x for x in items if x['interaction_type']=='QUESTION_ANSWERED'][-1];assert ans.get('asked_at') and ans.get('answered_at') and ans.get('response')=='Small events'

def test_v614_changes_not_duplicated_in_general_human_ledger():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);o.generate_next(o.start(init,'RUN-TEST','mock'));o.decide(st.load_state(),'CHANGES_REQUESTED','revise','tester');assert not st.list_human_interactions()

def test_v614_timeout_classification_and_targeted_retry():
 class TimeoutAdapter:
  def generate(self,system,user): raise TimeoutError('timed out after 900 seconds')
 with tempfile.TemporaryDirectory() as d:
  init=yaml.safe_load((ROOT/'intake/examples/consumer-event-planner.yaml').read_text());i=init['initiative']['initiative_id'];st=LocalStore(d,i,'RUN-T');o=ProductOrchestrator(ROOT,st,TimeoutAdapter());s=o.start(init,'RUN-T','timeout');assert o.generate_next(s) is None;s=st.load_state();assert s['stage']=='PROVIDER_TIMEOUT';r=o.retry_pending_generation(s,'tester','retry');assert r['artifact_type']=='PRODUCT_CHARTER';assert not o.completion(st.load_state())['blockers']

def test_v614_downstream_major_does_not_block_product_definition():
 class ReviewAdapter:
  def generate(self,system,user):
   if user.startswith('Independently review'):
    return {'pass':False,'findings':[{'severity':'MAJOR','finding':'Security design open','remediation':'Route to security','classification':'DOWNSTREAM_DEPENDENCY_REQUIRED','owner':'security-factory','route_to':['security-factory'],'blocks_product_definition':False,'blocks_implementation':True,'affected_gate':'IMPLEMENTATION_READINESS'}]}
   typ=user.split('OUTPUT_TYPE: ',1)[1].split('\n',1)[0];return {'artifact_type':typ,'title':typ,'summary':'ok','content':{},'evidence_status':'UNKNOWN','open_questions':[],'warnings':[],'traceability':[],'affected_outputs':[]}
 with tempfile.TemporaryDirectory() as d:
  init=yaml.safe_load((ROOT/'intake/examples/consumer-event-planner.yaml').read_text());i=init['initiative']['initiative_id'];st=LocalStore(d,i,'RUN-D');o=ProductOrchestrator(ROOT,st,ReviewAdapter());a=o.generate_next(o.start(init,'RUN-D','review'));assert a is not None;assert a['quality_review']['product_definition_readiness'] in {'PASS','PASS_WITH_CONDITIONS'};assert a['quality_review']['implementation_readiness'] in {'CONDITIONAL','NOT_READY'}

def test_v614_backfill_is_idempotent():
 with tempfile.TemporaryDirectory() as d:
  init,st,o=setup(d);o.generate_next(o.start(init,'RUN-TEST','mock'));o.decide(st.load_state(),'APPROVED',actor='tester');before=len(st.list_human_interactions());st.backfill_human_interactions();mid=len(st.list_human_interactions());st.backfill_human_interactions();after=len(st.list_human_interactions());assert before==mid==after

if __name__=='__main__':

 test_session_and_rework();test_isolation();test_full_creation_completion();test_v612_markdown_is_human_readable();test_v612_question_classification_and_actions();test_v612_schema_failure_never_references_unbound_review();test_v613_approval_context_propagates_and_no_duplicate_approval_question();test_v613_prior_revision_propagates_on_rework();test_v613_retry_clears_stale_information_request();test_v614_human_approval_and_answer_audit();test_v614_changes_not_duplicated_in_general_human_ledger();test_v614_timeout_classification_and_targeted_retry();test_v614_downstream_major_does_not_block_product_definition();test_v614_backfill_is_idempotent();print('V6.1.4 RUNTIME TESTS PASSED')
