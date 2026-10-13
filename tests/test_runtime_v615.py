"""v6.1.5 focused tests: governed BACKWARD Product Definition blocker resolution."""
from pathlib import Path
import tempfile
from runtime.stores.local import LocalStore
from runtime.orchestrator.product import ProductOrchestrator

ROOT=Path(__file__).resolve().parents[1]

class ResolutionAdapter:
    def generate(self, *, system, user):
        if not user.startswith('PRODUCT_DEFINITION_BLOCKER_RESOLUTION'):
            return {'pass': True, 'findings': []}
        if 'RECORDED_HUMAN_DECISIONS:\n[]' in user:
            return {
                'resolution_status':'HUMAN_DECISION_REQUIRED',
                'resolution_summary':'A material Product Owner decision is required.',
                'authoritative_business_rules':[], 'acceptance_intent':[],
                'human_decisions':[{'question':'Approve the proposed business rule?','recommendation':'YES','options':['YES','NO'],'reason':'Material product behavior.'}],
                'downstream_dependencies':[], 'evidence_refs':[]}
        return {
            'resolution_status':'RESOLVED','resolution_summary':'Resolved using the recorded human decision.',
            'authoritative_business_rules':['Apply the recorded Product Owner decision.'],
            'acceptance_intent':['The governed requirement reflects the recorded decision.'],
            'human_decisions':[], 'downstream_dependencies':['Technical enforcement remains downstream.'],
            'evidence_refs':['RECORDED_HUMAN_DECISION']}

def make_runtime():
    rt=Path(tempfile.mkdtemp())/'.runtime';sid='RUN-TEST-615';iid='INIT-TEST-615';st=LocalStore(rt,iid,sid)
    state={'initiative_id':iid,'session_id':sid,'correlation_id':'corr','initiative':{'initiative_id':iid,'title':'Test','development_context':'PRODUCT_CREATION'},'factory_id':'product-factory','adapter':'mock','workflow_state':'PAUSED_BLOCKED','stage':'QUALITY_REVIEW_FAILED','required_outputs':['PRODUCT_FEATURES','PRD'],'artifacts':{},'pending_approvals':[],'pending_actions':[],'open_questions':[],'open_alerts':[],'final_product_review_passed':False,'rework_feedback':{},'active_generation':{'artifact_type':'PRD','agent_id':'requirements','attempt':3,'failure_type':'QUALITY_REVIEW_FAILED'}}
    aid=f'{iid}-{sid}-PRODUCT_FEATURES';artifact={'artifact_id':aid,'artifact_type':'PRODUCT_FEATURES','version':'1','status':'HUMAN_REVIEW_REQUIRED','initiative_id':iid,'session_id':sid,'owner_agent':'requirements','payload':{'artifact_type':'PRODUCT_FEATURES','title':'Features','summary':'Approved features','content':{},'evidence_status':'DECISION','open_questions':[],'warnings':[],'traceability':[],'affected_outputs':[]}}
    st.save_artifact(iid,artifact);state['artifacts']['PRODUCT_FEATURES']={'artifact_id':aid,'version':'1','status':'APPROVED'}
    st.save_approval(iid,{'approval_id':'APR-1','initiative_id':iid,'session_id':sid,'artifact_id':aid,'artifact_version':'1','decision':'APPROVED','decided_by':'tester','decided_at':st.now(),'comments':None})
    findings=[]
    for n in range(1,5):
        findings.append({'severity':'BLOCKER','finding':f'DEP-PRD-00{n} material Product rule is unresolved.','remediation':'Resolve through Discovery and Workflow.','classification':'PRODUCT_DEFINITION_GAP','owner':'Discovery and Workflow','route_to':['Discovery Product agent','Workflow Product agent','Requirements agent'],'blocks_product_definition':True,'blocks_implementation':True,'affected_gate':'PRODUCT_DEFINITION_READINESS'})
    state['open_alerts']=[{'alert_id':'ALERT-1','severity':'BLOCKER','type':'QUALITY_REVIEW_FAILED','artifact_type':'PRD','agent_id':'requirements','attempt':3,'details':{'product_definition_readiness':'FAIL','implementation_readiness':'NOT_READY','findings':findings},'resolved':False,'created_at':st.now()}]
    # Provide the approved upstream context required by v6.1.6.
    upstream_types = [
        "PRODUCT_CHARTER",
        "PRODUCT_BRIEF",
        "PERSONAS",
        "PAIN_POINT_ANALYSIS",
        "USE_CASES",
        "PRODUCT_CAPABILITIES",
    ]

    for artifact_type in upstream_types:
        artifact_id = f"{iid}-{sid}-{artifact_type}"

        upstream_artifact = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "version": "1",
            "status": "HUMAN_REVIEW_REQUIRED",
            "initiative_id": iid,
            "session_id": sid,
            "owner_agent": "product-lead",
            "payload": {
                "artifact_type": artifact_type,
                "title": f"Test {artifact_type}",
                "summary": f"Approved test context for {artifact_type}",
                "content": {
                    "business_context": "Fixture data for backward-resolution testing."
                },
                "evidence_status": "DECISION",
                "open_questions": [],
                "warnings": [],
                "traceability": [],
                "affected_outputs": [],
            },
        }

        st.save_artifact(iid, upstream_artifact)

        state["artifacts"][artifact_type] = {
            "artifact_id": artifact_id,
            "version": "1",
            "status": "APPROVED",
        }

        st.save_approval(
            iid,
            {
                "approval_id": f"APR-{artifact_type}",
                "initiative_id": iid,
                "session_id": sid,
                "artifact_id": artifact_id,
                "artifact_version": "1",
                "decision": "APPROVED",
                "decided_by": "tester",
                "decided_at": st.now(),
                "comments": "Test fixture approval",
            },
        )

    st.save_state(state)
    return st, ProductOrchestrator(ROOT, st, ResolutionAdapter())

def main():
    st,o=make_runtime();r=o.resolve_blockers(st.load_state(),actor='tester');assert r['status']=='WAITING_FOR_HUMAN';assert r['blocker_id']=='DEP-PRD-001'
    while r['status']!='RESOLVED':
        s=st.load_state();assert len(s['open_questions'])==1;o.answer(s,'YES','tester');r=o.resolve_blockers(st.load_state(),actor='tester')
    assert r['resolution_refs']==['DEP-PRD-001','DEP-PRD-002','DEP-PRD-003','DEP-PRD-004']
    s=st.load_state();assert s['workflow_state']=='READY_TO_RUN';assert s['resolution_workflow']['status']=='RESOLVED';assert s['open_alerts'][0]['resolved'] is True
    assert len(st.list_resolutions('PRD'))==4
    assert len([x for x in st.list_human_interactions() if x['interaction_type']=='QUESTION_ANSWERED'])==4
    ctx=o._context_package(s,'PRD');assert len(ctx['product_definition_resolutions'])==4
    print('V6.1.5 RUNTIME TESTS PASSED')
if __name__=='__main__':main()
