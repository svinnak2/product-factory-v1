"""Product Factory v6.1.5: governed HITL, context assembly, quality semantics, recovery and audit."""
from pathlib import Path
import yaml,json,uuid,datetime,subprocess,re
from runtime.validators.core import validate_artifact, Draft202012Validator

class ProductOrchestrator:
    PRODUCT_OWNERS={'product-lead','product-discovery','requirements','workflow-journey','ai-product-strategy','product-analytics','product-review-routing','PRODUCT_OWNER'}
    def __init__(self,platform_root,store,adapter):
        self.root=Path(platform_root); self.pf=self.root/'product-factory'; self.store=store; self.adapter=adapter
        self.catalog=yaml.safe_load((self.pf/'orchestration/output-catalog.yaml').read_text())['outputs']; self.profiles=yaml.safe_load((self.pf/'orchestration/completion-profiles.yaml').read_text())['profiles']; self.quality=yaml.safe_load((self.pf/'orchestration/quality-standards.yaml').read_text()); self.schema=self.pf/'schemas/executable-artifact.schema.json'; self.resolution_schema=self.pf/'schemas/product-definition-resolution.schema.json'
    def now(self): return self.store.now()
    def emit(self,s,typ,msg,severity='INFO',**kw):
        e={'schema_version':'1.1','event_id':str(uuid.uuid4()),'event_type':typ,'initiative_id':s['initiative_id'],'session_id':s['session_id'],'correlation_id':s['correlation_id'],'factory_id':'product-factory','timestamp':self.now(),'message':msg,'severity':severity,**kw}; self.store.append_event(e); return e
    def _human(self,s,interaction_type,actor,**kw):
        r={'schema_version':'1.0','interaction_id':'HI-'+str(uuid.uuid4()),'interaction_type':interaction_type,'timestamp':self.now(),'actor':actor,'actor_type':'HUMAN','initiative_id':s['initiative_id'],'session_id':s['session_id'],'factory_id':'product-factory','immutable':True,**kw}; self.store.append_human_interaction(r); return r
    def start(self,initiative,session_id,adapter_name):
        i=initiative['initiative']; req=list(self.profiles[i['development_context']]['required_outputs']); s={'initiative_id':i['initiative_id'],'session_id':session_id,'correlation_id':str(uuid.uuid4()),'initiative':i,'factory_id':'product-factory','adapter':adapter_name,'workflow_state':'READY_TO_RUN','stage':'INTAKE','required_outputs':req,'artifacts':{},'pending_approvals':[],'pending_actions':[],'open_questions':[],'open_alerts':[],'final_product_review_passed':False,'rework_feedback':{},'active_generation':None}; self.store.save_state(s); self.emit(s,'WORKFLOW_STARTED',f"Product Factory session started: {i['title']}"); return s
    def next_ready(self,s):
        for typ in s['required_outputs']:
            if s['artifacts'].get(typ,{}).get('status')=='APPROVED': continue
            if all(s['artifacts'].get(d,{}).get('status')=='APPROVED' for d in self.catalog[typ].get('depends_on',[])): return typ
    def _approval_envelope(self,s,typ,include_artifact=True):
        m=s['artifacts'][typ]; art=self.store.load_artifact(s['initiative_id'],m['artifact_id'],m['version']); approval=self.store.latest_approval(m['artifact_id'],m['version'],'APPROVED')
        if m.get('status')!='APPROVED' or not approval: raise ValueError(f'Approved dependency {typ} is missing its immutable runtime approval record')
        env={'governance':{'artifact_id':m['artifact_id'],'artifact_type':typ,'version':str(m['version']),'status':'APPROVED','approval_id':approval['approval_id'],'approval_type':'HUMAN','approved_by':approval.get('decided_by'),'approved_at':approval.get('decided_at'),'comments':approval.get('comments'),'session_id':s['session_id'],'initiative_id':s['initiative_id']}}
        if include_artifact: env['artifact']=art['payload']
        return env
    def _prior_revision(self,s,typ):
        m=s.get('artifacts',{}).get(typ)
        if not m:return None
        try:return self.store.load_artifact(s['initiative_id'],m['artifact_id'],m['version'])
        except FileNotFoundError:return None
    def _upstream_dependencies(self, artifact_type):
        """Return all transitive upstream dependencies.

        Reject missing catalog entries and circular dependencies.
        """
        ancestors = set()
        visiting = set()
        visited = set()

        def visit(current):
            if current in visiting:
                raise ValueError(
                    f"Circular artifact dependency detected at {current}"
                )

            if current in visited:
                return

            if current not in self.catalog:
                raise ValueError(
                    f"Unknown artifact dependency: {current}"
                )

            visiting.add(current)

            for dependency in self.catalog[current].get(
                "depends_on", []
            ):
                visit(dependency)
                ancestors.add(dependency)

            visiting.remove(current)
            visited.add(current)

        visit(artifact_type)
        return ancestors
    def _context_package(self, s, typ):
        """Build an approval-verified, dependency-aware context package."""
        direct = set(self.catalog[typ].get("depends_on", []))
        upstream = self._upstream_dependencies(typ)

        package = {
            "direct_dependencies": {},
            "approved_provenance": {},
            "governing_materials": {},
        }

        # Validate the entire upstream dependency set before loading
        # artifacts or their approval records.
        missing = sorted(
            dependency
            for dependency in upstream
            if dependency not in s.get("artifacts", {})
        )

        if missing:
            raise ValueError(
                "Required upstream artifact is missing: "
                + ", ".join(missing)
            )

        # Every upstream dependency must have verified approval evidence.
        for dependency in sorted(upstream):
            envelope = self._approval_envelope(
                s, dependency, include_artifact=True
            )

            if dependency in direct:
                package["direct_dependencies"][dependency] = envelope
            else:
                package["approved_provenance"][dependency] = envelope

        # Other approved artifacts provide background provenance only.
        for dependency, metadata in s.get("artifacts", {}).items():
            if dependency in upstream or dependency == typ:
                continue

            if metadata.get("status") != "APPROVED":
                continue

            try:
                envelope = self._approval_envelope(
                    s, dependency, include_artifact=False
                )

                artifact = self.store.load_artifact(
                    s["initiative_id"],
                    metadata["artifact_id"],
                    metadata["version"],
                )["payload"]

                envelope["summary"] = {
                    "title": artifact.get("title"),
                    "summary": artifact.get("summary"),
                    "evidence_status": artifact.get("evidence_status"),
                    "traceability": artifact.get("traceability", [])[:40],
                }

                package["approved_provenance"][dependency] = envelope

            except Exception:
                # Optional background provenance is not a dependency.
                continue

        owner = self.catalog[typ]["owner"]

        package["governing_materials"] = {
            "owner_agent": owner,
            "agent_definition": str(
                self.pf / "agents" / owner / "AGENT.md"
            ),
            "skills": str(
                self.pf / "agents" / owner / "SKILLS.md"
            ),
            "schema": str(self.schema),
            "quality_standards": (
                self.quality["minimum_quality"].get("all", [])
                + self.quality["minimum_quality"].get(typ, [])
            ),
            "orchestration_policy": str(
                self.pf / "orchestration/orchestration-policy.yaml"
            ),
        }

        resolutions = [
            record
            for record in self.store.list_resolutions(typ)
            if record.get("status") == "RESOLVED"
        ]

        if resolutions:
            package["product_definition_resolutions"] = resolutions

        return package
    def _prompt(self,s,typ,context,last,prior=None):
        rules="\nGOVERNANCE_RULES:\n- Approved dependencies/provenance are immutable human-approved evidence; never ask the human to reconfirm them.\n- Never fabricate customer evidence, business decisions, metrics, permissions, laws, policies or technical thresholds.\n- Distinguish PRODUCT DEFINITION readiness from IMPLEMENTATION readiness. Product artifacts may be Product-Definition-ready while downstream Architecture/Data/Security/Operations analysis remains open.\n- A downstream unknown must be nonblocking when Product can responsibly record it with owner, route_to, resolution_stage and affected gate/output.\n- Ask a blocking HUMAN_DECISION only for a NEW material Product-owner decision required now.\n- Product discovery/workflow questions are DISCOVERY_REQUIRED and nonblocking unless explicit human authority is required now.\n- Architecture/security/engineering/operations questions are DOWNSTREAM_ANALYSIS and nonblocking.\n- Unknown facts that can safely remain unresolved are ASSUMPTION_OR_UNKNOWN and nonblocking.\n- Do not place runtime/schema/retry/provider/internal-review mechanics in the governed business artifact.\nReturn ONE JSON object with artifact_type, title, summary, content, evidence_status, open_questions, warnings, traceability, affected_outputs. Every open question must include question, blocking, classification, owner, route_to, resolution_stage, reason."
        return 'OUTPUT_TYPE: '+typ+'\nINITIATIVE:\n'+json.dumps(s['initiative'],indent=2)+'\nAGENT_CONTEXT_PACKAGE:\n'+json.dumps(context,indent=2)+'\nPRIOR_REVISION_FOR_REWORK:\n'+json.dumps(prior,indent=2)+'\nHUMAN_REWORK_FEEDBACK:\n'+json.dumps(s.get('rework_feedback',{}).get(typ),indent=2)+'\nPRIOR_QUALITY_FINDINGS_TO_REMEDIATE:\n'+json.dumps(last,indent=2)+rules
    def _classify_questions(self,payload):
        for q in payload.get('open_questions',[]):
            cls=q.get('classification')
            if cls not in {'HUMAN_DECISION','DISCOVERY_REQUIRED','DOWNSTREAM_ANALYSIS','ASSUMPTION_OR_UNKNOWN'}: cls='HUMAN_DECISION' if q.get('blocking') else 'DISCOVERY_REQUIRED';q['classification']=cls
            if cls!='HUMAN_DECISION':q['blocking']=False
            q.setdefault('owner','PRODUCT_OWNER' if cls=='HUMAN_DECISION' else 'product-discovery' if cls=='DISCOVERY_REQUIRED' else 'specialist-factory' if cls=='DOWNSTREAM_ANALYSIS' else 'product-lead');q.setdefault('route_to',[] if cls!='DOWNSTREAM_ANALYSIS' else ['architecture-factory','security-factory']);q.setdefault('resolution_stage','PRODUCT_DEFINITION' if cls=='HUMAN_DECISION' else 'DISCOVERY' if cls=='DISCOVERY_REQUIRED' else 'DESIGN' if cls=='DOWNSTREAM_ANALYSIS' else 'AS_NEEDED');q.setdefault('status','OPEN')
        return payload
    def _failure(self,exc,phase='generation'):
        text=str(exc); low=text.lower()
        if isinstance(exc,subprocess.TimeoutExpired) or 'timed out after' in low:return 'PROVIDER_TIMEOUT'
        if 'not found' in low or 'unavailable' in low or 'connection' in low:return 'PROVIDER_UNAVAILABLE'
        if 'json' in low:return 'INVALID_MODEL_RESPONSE'
        return 'GENERATION_FAILED' if phase=='generation' else 'QUALITY_REVIEW_FAILED'
    def _normalize_findings(self,findings):
        out=[]
        for f in findings or []:
            x=dict(f); sev=x.get('severity','MAJOR'); owner=x.get('owner'); cls=x.get('classification')
            if cls not in {'PRODUCT_DEFINITION_GAP','DOWNSTREAM_DEPENDENCY_REQUIRED','ADVISORY'}:
                route=x.get('route_to') or []; route=[route] if isinstance(route,str) else route
                downstream=bool(route) and any(r not in self.PRODUCT_OWNERS for r in route)
                cls='DOWNSTREAM_DEPENDENCY_REQUIRED' if downstream else 'PRODUCT_DEFINITION_GAP' if sev in {'BLOCKER','MAJOR'} else 'ADVISORY'
            x['classification']=cls; x.setdefault('owner',owner or ('specialist-factory' if cls=='DOWNSTREAM_DEPENDENCY_REQUIRED' else 'product-lead')); x.setdefault('route_to',[]); x.setdefault('blocks_product_definition',cls=='PRODUCT_DEFINITION_GAP' and sev in {'BLOCKER','MAJOR'}); x.setdefault('blocks_implementation',sev in {'BLOCKER','MAJOR'}); x.setdefault('affected_gate','PRODUCT_DEFINITION' if x['blocks_product_definition'] else 'IMPLEMENTATION_READINESS'); out.append(x)
        return out
    def _quality_review(self,typ,payload,context):
        if typ=='PRODUCT_REVIEW_REPORT':return {'pass':True,'product_definition_readiness':'PASS','implementation_readiness':'CONDITIONAL','findings':[]}
        rdir=self.pf/'agents/product-review-routing';system=(rdir/'AGENT.md').read_text()+'\n\n'+(rdir/'SKILLS.md').read_text();standards=self.quality['minimum_quality'].get('all',[])+self.quality['minimum_quality'].get(typ,[])
        user='Independently review this governed Product artifact. Do not rewrite it. Evaluate PRODUCT_DEFINITION_READINESS separately from IMPLEMENTATION_READINESS. Do not fail Product Definition merely because a technical/downstream decision belongs to Architecture, Data, Security, Engineering, Operations, QE or Assurance, provided the artifact identifies the unresolved dependency, owner/route and resolution stage. Do fail Product Definition for missing material Product-owned scope, business rule, user need, acceptance intent or human-authority decision that must be settled now. Return ONLY JSON with: pass (boolean; true iff Product Definition has no blocking gap), product_definition_readiness (PASS|PASS_WITH_CONDITIONS|FAIL), implementation_readiness (READY|CONDITIONAL|NOT_READY), findings (array). Every finding: severity BLOCKER|MAJOR|MINOR|ADVISORY, finding, remediation, classification PRODUCT_DEFINITION_GAP|DOWNSTREAM_DEPENDENCY_REQUIRED|ADVISORY, owner, route_to, blocks_product_definition boolean, blocks_implementation boolean, affected_gate.\nQUALITY_STANDARDS:'+json.dumps(standards)+'\nCONTEXT_PROVENANCE:'+json.dumps(context)+'\nARTIFACT:'+json.dumps(payload)
        try:
            r=self.adapter.generate(system=system,user=user)
            if not isinstance(r,dict) or 'findings' not in r:raise ValueError('invalid review response')
            r['findings']=self._normalize_findings(r.get('findings')); blocking=[f for f in r['findings'] if f.get('blocks_product_definition') and f.get('severity') in {'BLOCKER','MAJOR'}];r['pass']=not blocking;r.setdefault('product_definition_readiness','PASS' if not blocking else 'FAIL');r.setdefault('implementation_readiness','CONDITIONAL' if r['findings'] else 'READY');return r
        except Exception as e:return {'pass':False,'runtime_error':{'type':self._failure(e,'review'),'message':str(e)},'product_definition_readiness':'NOT_EVALUATED','implementation_readiness':'NOT_EVALUATED','findings':[]}
    def _block(self,s,typ,owner,failure_type,details,attempt=None):
        alert={'alert_id':str(uuid.uuid4()),'severity':'BLOCKER','type':failure_type,'artifact_type':typ,'agent_id':owner,'attempt':attempt,'details':details,'resolved':False,'created_at':self.now()};s['open_alerts'].append(alert);s['workflow_state']='PAUSED_BLOCKED';s['stage']=failure_type;s['active_generation']={'artifact_type':typ,'agent_id':owner,'attempt':attempt,'failure_type':failure_type};self.store.save_state(s);self.emit(s,'BLOCKER_RAISED',f'{typ} blocked: {failure_type}.','BLOCKER',artifact_type=typ,agent_id=owner,attempt=attempt,failure_type=failure_type,details=details);return None
    def generate_next(self,s):
        typ=self.next_ready(s)
        if not typ:return None
        owner=self.catalog[typ]['owner'];s['workflow_state']='RUNNING';s['stage']='PRODUCT_DEFINITION';s['active_generation']={'artifact_type':typ,'agent_id':owner,'attempt':0,'failure_type':None};self.store.save_state(s);ad=self.pf/'agents'/owner;system=(ad/'AGENT.md').read_text()+'\n\n'+(ad/'SKILLS.md').read_text();context=self._context_package(s,typ);prior=self._prior_revision(s,typ);self.emit(s,'TASK_STARTED',f'{owner} generating {typ}',agent_id=owner,task=typ);last=[];payload=None;review=None;max_attempts=int(self.quality['review'].get('max_generation_attempts',3))
        for attempt in range(1,max_attempts+1):
            s['active_generation']['attempt']=attempt;self.store.save_state(s)
            try:payload=self.adapter.generate(system=system,user=self._prompt(s,typ,context,last,prior))
            except Exception as e:
                ft=self._failure(e);self.emit(s,'MODEL_ERROR',f'{typ} generation attempt {attempt} failed: {e}','WARNING',agent_id=owner,failure_type=ft,attempt=attempt)
                if ft in {'PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE'}:return self._block(s,typ,owner,ft,{'message':str(e)},attempt)
                last=[{'severity':'BLOCKER','finding':'Model invocation failed','remediation':str(e),'classification':'PRODUCT_DEFINITION_GAP','blocks_product_definition':True}];continue
            payload=self._classify_questions(payload);errors=validate_artifact(payload,self.schema,typ)
            if errors:return self._block(s,typ,owner,'SCHEMA_VALIDATION_FAILED',{'errors':errors},attempt)
            blocking=[q for q in payload.get('open_questions',[]) if q.get('blocking')]
            if blocking:
                asked_at=self.now()
                for q in blocking:q.setdefault('question_id','Q-'+str(uuid.uuid4()));q.setdefault('asked_at',asked_at)
                s['workflow_state']='PAUSED_WAITING_FOR_HUMAN';s['stage']='HUMAN_DECISION_REQUIRED';s['open_questions'].extend(blocking);s['pending_actions']=[{'type':'DECISION_REQUIRED','question_id':q['question_id'],'question':q.get('question'),'blocking':True,'asked_at':q['asked_at']} for q in blocking];s['active_generation']={'artifact_type':typ,'agent_id':owner,'attempt':attempt,'failure_type':'HUMAN_DECISION_REQUIRED'};self.store.save_state(s);self.emit(s,'INFORMATION_REQUESTED',f'{typ} requires human information.','BLOCKER',agent_id=owner,details=blocking);return None
            review=self._quality_review(typ,payload,context)
            if review.get('runtime_error'):return self._block(s,typ,owner,review['runtime_error']['type'],review['runtime_error'],attempt)
            last=review.get('findings',[]);blocking=[f for f in last if f.get('blocks_product_definition') and f.get('severity') in self.quality['review']['blocking_severities']]
            if not blocking:break
            self.emit(s,'QUALITY_REWORK',f'{typ} failed Product Definition review on attempt {attempt}; regenerating.','WARNING',agent_id=owner,details=blocking)
        if payload is None:return self._block(s,typ,owner,'GENERATION_FAILED',{'findings':last},max_attempts)
        blocking=[f for f in (review or {}).get('findings',[]) if f.get('blocks_product_definition') and f.get('severity') in self.quality['review']['blocking_severities']]
        if blocking:return self._block(s,typ,owner,'QUALITY_REVIEW_FAILED',{'product_definition_readiness':review.get('product_definition_readiness'),'implementation_readiness':review.get('implementation_readiness'),'findings':review.get('findings',[])},max_attempts)
        prev=s['artifacts'].get(typ);ver=str(int(prev['version'])+1) if prev else '1';aid=f'{s["initiative_id"]}-{s["session_id"]}-{typ}';artifact={'artifact_id':aid,'artifact_type':typ,'version':ver,'status':'HUMAN_REVIEW_REQUIRED','initiative_id':s['initiative_id'],'session_id':s['session_id'],'owner_agent':owner,'quality_review':review,'generated_at':self.now(),'payload':payload};self.store.save_artifact(s['initiative_id'],artifact);s['artifacts'][typ]={'artifact_id':aid,'version':ver,'status':'HUMAN_REVIEW_REQUIRED'};s['pending_approvals']=[{'artifact_id':aid,'artifact_type':typ,'version':ver,'human_review_requested_at':self.now()}];s['pending_actions']=[{'type':'ARTIFACT_REVIEW_REQUIRED','artifact_id':aid,'artifact_type':typ,'version':ver}];s['workflow_state']='PAUSED_WAITING_FOR_HUMAN';s['stage']='HUMAN_REVIEW';s['active_generation']=None;self.store.save_state(s);self.emit(s,'APPROVAL_REQUIRED',f'Human review required for {typ} v{ver}.','APPROVAL_REQUIRED',agent_id=owner,artifact_id=aid);return artifact
    def decide(self,s,decision,comments=None,actor='human'):
        if not s['pending_approvals']:raise ValueError('No pending approval')
        p=s['pending_approvals'][0];typ=p['artifact_type'];decided_at=self.now();approval={'approval_id':str(uuid.uuid4()),'initiative_id':s['initiative_id'],'session_id':s['session_id'],'artifact_id':p['artifact_id'],'artifact_version':p['version'],'decision':decision,'decided_by':actor,'decided_at':decided_at,'comments':comments};self.store.save_approval(s['initiative_id'],approval);s['pending_approvals']=[];s['pending_actions']=[]
        if decision=='APPROVED':
            s['artifacts'][typ]['status']='APPROVED';s['workflow_state']='READY_TO_RUN';s['stage']='PRODUCT_DEFINITION';s.get('rework_feedback',{}).pop(typ,None);hi=self._human(s,'ARTIFACT_APPROVAL',actor,artifact_type=typ,artifact_id=p['artifact_id'],artifact_version=p['version'],approval_id=approval['approval_id'],decision='APPROVED',comments=comments,source_type='APPROVAL',source_id=approval['approval_id']);self.emit(s,'ARTIFACT_APPROVED',f'{typ} v{p["version"]} approved.',artifact_id=p['artifact_id'],interaction_id=hi['interaction_id'],approved_at=decided_at)
            if typ=='PRODUCT_REVIEW_REPORT':s['final_product_review_passed']=True
            if typ=='CHANGE_IMPACT_ANALYSIS':
                art=self.store.load_artifact(s['initiative_id'],p['artifact_id'],p['version']);affected=[x for x in art['payload'].get('affected_outputs',[]) if x in self.catalog and x!='CHANGE_IMPACT_ANALYSIS']
                for x in affected+['PRODUCT_REVIEW_REPORT','DOWNSTREAM_ROUTING_PLAN','PRODUCT_PACKAGE']:
                    if x not in s['required_outputs']:s['required_outputs'].append(x)
        else:
            s['artifacts'][typ]['status']=decision;s['workflow_state']='READY_TO_RUN';s['stage']='REWORK';s.setdefault('rework_feedback',{})[typ]={'decision':decision,'comments':comments,'artifact_version':p['version'],'at':decided_at};self.emit(s,'CHANGES_REQUESTED' if decision=='CHANGES_REQUESTED' else 'ARTIFACT_REJECTED',f'{typ} v{p["version"]} requires rework.','WARNING',artifact_id=p['artifact_id'],details={'comments':comments})
        self.store.save_state(s)
    def answer(self, s, answer, actor='human'):
        if not s['open_questions']:
            raise ValueError('No open question')

        q = s['open_questions'].pop(0)
        answered_at = self.now()

        hi = self._human(
            s,
            'QUESTION_ANSWERED',
            actor,
            question_id=q.get('question_id'),
            question=q['question'],
            asked_at=q.get('asked_at'),
            answered_at=answered_at,
            response=answer,
            classification='BUSINESS_REQUIREMENT_INPUT',
            question_classification=q.get('classification'),
            source='HUMAN',
            source_type='CLARIFICATION',
            source_id=q.get('question_id') or 'HI-ANSWER',
            blocker_id=q.get('blocker_id'),
            artifact_type=q.get('artifact_type'),
        )

        s['initiative'].setdefault(
            'human_clarifications', []
        ).append({
            'interaction_id': hi['interaction_id'],
            'question_id': q.get('question_id'),
            'question': q['question'],
            'answer': answer,
            'answered_by': actor,
            'asked_at': q.get('asked_at'),
            'answered_at': answered_at,
            'at': answered_at,
            'blocker_id': q.get('blocker_id'),
            'artifact_type': q.get('artifact_type'),
        })

        rw = s.get('resolution_workflow') or {}
        is_resolution_question = (
            bool(q.get('blocker_id'))
            and rw.get('status') == 'ACTIVE'
        )

        if is_resolution_question:
            target = rw['artifact_type']
            blocker_id = q['blocker_id']

            rec = self.store.load_resolution(
                target, blocker_id
            )

            if rec is None:
                raise ValueError(
                    f'Missing resolution record for {blocker_id}'
                )

            rec.setdefault('human_decisions', []).append({
                'question_id': q.get('question_id'),
                'question': q['question'],
                'answer': answer,
                'answered_by': actor,
                'asked_at': q.get('asked_at'),
                'answered_at': answered_at,
                'interaction_id': hi['interaction_id'],
            })

            # Remove only the decision that was answered.
            rec['pending_human_decisions'] = [
                pending
                for pending in rec.get(
                    'pending_human_decisions', []
                )
                if pending.get('question_id')
                != q.get('question_id')
            ]

            remaining_for_blocker = [
                pending
                for pending in s['open_questions']
                if pending.get('blocker_id') == blocker_id
            ]

            if remaining_for_blocker:
                rec['status'] = 'WAITING_FOR_HUMAN'
            else:
                rec['status'] = 'IN_PROGRESS'

            rec['updated_at'] = answered_at

            self.store.save_resolution(
                target, blocker_id, rec
            )

        # Rebuild pending actions from outstanding questions.
        remaining_questions = s['open_questions']

        s['pending_actions'] = [
            {
                'type': 'DECISION_REQUIRED',
                'question_id': pending.get('question_id'),
                'question': pending.get('question'),
                'blocker_id': pending.get('blocker_id'),
                'blocking': pending.get('blocking', True),
                'asked_at': pending.get('asked_at'),
            }
            for pending in remaining_questions
        ]

        if remaining_questions:
            # Do not resume while any human decisions remain.
            s['workflow_state'] = 'PAUSED_WAITING_FOR_HUMAN'
            s['stage'] = 'HUMAN_DECISION_REQUIRED'

        elif is_resolution_question:
            # All current human questions are answered.
            # The resolver must still validate the blocker.
            s['workflow_state'] = 'READY_TO_RUN'
            s['stage'] = 'BACKWARD_RESOLUTION'
            s['active_generation'] = {
                'artifact_type': rw['artifact_type'],
                'agent_id': 'product-lead',
                'attempt': None,
                'failure_type': None,
            }

        else:
            s['workflow_state'] = 'READY_TO_RUN'
            s['stage'] = 'PRODUCT_DEFINITION'
            s['active_generation'] = None

        self.store.save_state(s)

        if remaining_questions:
            self.emit(
                s,
                'HUMAN_DECISION_RECORDED',
                'Human decision recorded; additional decisions remain.',
                interaction_id=hi['interaction_id'],
                blocker_id=q.get('blocker_id'),
                details={
                    'remaining_questions': len(
                        remaining_questions
                    )
                },
            )
        else:
            self.emit(
                s,
                'WORKFLOW_RESUMED',
                'All pending human questions answered; workflow ready to resume.',
                interaction_id=hi['interaction_id'],
                blocker_id=q.get('blocker_id'),
            )
    def record_human_input(self,s,text,interaction_type='BUSINESS_REQUIREMENT_INPUT',actor='human',classification=None,supersedes=None):
        allowed={'BUSINESS_REQUIREMENT_INPUT','BUSINESS_REQUIREMENT_QUESTION','CLARIFICATION_PROVIDED','BUSINESS_DECISION','SCOPE_DECISION','CONSTRAINT_PROVIDED','ASSUMPTION_CONFIRMED','RISK_DECISION','PRIORITY_DECISION','HUMAN_DIRECTION'}
        if interaction_type not in allowed:raise ValueError('Unsupported human interaction type')
        hi=self._human(s,interaction_type,actor,text=text,classification=classification,source='HUMAN',supersedes_interaction_id=supersedes);s['initiative'].setdefault('human_inputs',[]).append({'interaction_id':hi['interaction_id'],'interaction_type':interaction_type,'text':text,'actor':actor,'timestamp':hi['timestamp'],'classification':classification,'supersedes_interaction_id':supersedes});self.store.save_state(s);self.emit(s,'HUMAN_INPUT_RECORDED',f'Human input recorded: {interaction_type}.',interaction_id=hi['interaction_id']);return hi
    def _blocker_id(self,artifact_type,finding,index):
        text=(finding.get('finding','')+' '+finding.get('remediation',''))
        m=re.search(r'\bDEP-[A-Z0-9_-]+-\d+\b',text)
        return m.group(0) if m else f'PDB-{artifact_type}-{index:03d}'
    def _resolution_agents(self,finding):
        text=' '.join([str(finding.get('owner',''))]+[str(x) for x in (finding.get('route_to') or [])]).lower();agents=[]
        if 'discovery' in text: agents.append('product-discovery')
        if 'workflow' in text: agents.append('workflow-journey')
        if not agents: agents.append('product-lead')
        return list(dict.fromkeys(agents))
    def _resolution_system(self,agents):
        parts=[]
        for agent in agents:
            d=self.pf/'agents'/agent
            if d.exists(): parts.extend([(d/'AGENT.md').read_text(),(d/'SKILLS.md').read_text()])
        lead=self.pf/'agents/product-lead';parts.extend([(lead/'AGENT.md').read_text(),(lead/'SKILLS.md').read_text()]);return '\n\n'.join(parts)
    def _resolution_prompt(self,s,target,item,existing):
        context=self._context_package(s,target);finding=item['finding'];decisions=(existing or {}).get('human_decisions',[])
        template="""PRODUCT_DEFINITION_BLOCKER_RESOLUTION
ARTIFACT_TYPE: %s
BLOCKER_ID: %s
FINDING:
%s
APPROVED_CONTEXT:
%s
RECORDED_HUMAN_DECISIONS:
%s

Resolve this Product Definition blocker using BACKWARD orchestration. Use only approved evidence and recorded human decisions as authoritative facts. You may propose reasonable product semantics, but if choosing among alternatives would materially change scope, authority, access, lifecycle, limits, agreement semantics, risk acceptance, or another Product Owner decision, do not silently choose: request a targeted human decision. Do not make architecture, security-enforcement, implementation, database, cloud-service, or other downstream technical decisions.
Return ONLY JSON with: resolution_status (RESOLVED|HUMAN_DECISION_REQUIRED), resolution_summary, authoritative_business_rules (array), acceptance_intent (array), human_decisions (array of objects with question, recommendation, options, reason), downstream_dependencies (array), evidence_refs (array). When recorded human decisions answer prior questions, incorporate them and continue resolution."""
        return template%(target,item['blocker_id'],json.dumps(finding,indent=2),json.dumps(context,indent=2),json.dumps(decisions,indent=2))
    def _latest_quality_blocker(self,s,artifact_type=None):
        alerts=[a for a in s.get('open_alerts',[]) if a.get('severity')=='BLOCKER' and not a.get('resolved') and a.get('type')=='QUALITY_REVIEW_FAILED']
        if artifact_type: alerts=[a for a in alerts if a.get('artifact_type')==artifact_type]
        return alerts[-1] if alerts else None
    def start_blocker_resolution(self,s,artifact_type=None,actor='human'):
        if s.get('pending_approvals'): raise ValueError('Cannot resolve blockers while an artifact awaits human review')
        alert=self._latest_quality_blocker(s,artifact_type)
        if not alert: raise ValueError('No unresolved QUALITY_REVIEW_FAILED Product Definition blocker is available')
        target=alert.get('artifact_type');findings=(alert.get('details') or {}).get('findings',[]);blocking=[f for f in findings if f.get('classification')=='PRODUCT_DEFINITION_GAP' and f.get('blocks_product_definition') and f.get('severity') in {'BLOCKER','MAJOR'}]
        if not blocking: raise ValueError('Quality blocker has no structured PRODUCT_DEFINITION_GAP findings')
        items=[{'blocker_id':self._blocker_id(target,f,n),'finding':f,'agents':self._resolution_agents(f),'status':'PENDING'} for n,f in enumerate(blocking,1)]
        plan={'schema_version':'1.0','initiative_id':s['initiative_id'],'session_id':s['session_id'],'artifact_type':target,'source_alert_id':alert.get('alert_id'),'mode':'BACKWARD','status':'ACTIVE','created_at':self.now(),'created_by':actor,'items':items}
        self.store.save_resolution_plan(target,plan);s['resolution_workflow']={'status':'ACTIVE','artifact_type':target,'source_alert_id':alert.get('alert_id'),'started_at':plan['created_at']};s['workflow_state']='READY_TO_RUN';s['stage']='BACKWARD_RESOLUTION';s['active_generation']={'artifact_type':target,'agent_id':'product-lead','attempt':None,'failure_type':None};self.store.save_state(s);self.emit(s,'BACKWARD_ORCHESTRATION_STARTED',f'{target} Product Definition blocker resolution started.',details={'blockers':[x['blocker_id'] for x in items],'mode':'BACKWARD'});return plan
    def _pending_blocker_decisions(self, s, target, blocker_id):
        """Return unanswered human decisions linked to a blocker."""

        rec = self.store.load_resolution(target, blocker_id) or {}

        pending = {}

        for question in rec.get('pending_human_decisions', []):
            if question.get('status', 'OPEN') == 'OPEN':
                key = question.get('question_id') or question.get('question')
                pending[key] = question

        for question in s.get('open_questions', []):
            if (
                question.get('blocker_id') == blocker_id
                and question.get('status', 'OPEN') == 'OPEN'
            ):
                key = question.get('question_id') or question.get('question')
                pending[key] = question

        return list(pending.values())
    def _block_resolution_failure(
        self, s, target, agents, failure_type, details
    ):
        """Persist a blocked resolution and return a structured result."""
        self._block(
            s,
            target,
            agents,
            failure_type,
            details,
        )

        return {
            'status': 'BLOCKED',
            'artifact_type': target,
            'blocker_id': details.get('blocker_id'),
            'failure_type': failure_type,
            'message': details.get(
                'message', 'Blocker resolution failed'
            ),
        }
    def resolve_blockers(self,s,artifact_type=None,actor='human'):
        rw=s.get('resolution_workflow') or {}
        if rw.get('status')!='ACTIVE': self.start_blocker_resolution(s,artifact_type,actor);s=self.store.load_state();rw=s['resolution_workflow']
        target=rw['artifact_type'];plan=self.store.load_resolution_plan(target)
        if not plan: raise ValueError('Resolution plan is missing')
        for item in plan['items']:
            blocker_id = item['blocker_id']
            existing = self.store.load_resolution(target, blocker_id)

            pending = self._pending_blocker_decisions(
                s, target, blocker_id
            )

            if pending:
                item['status'] = 'WAITING_FOR_HUMAN'
                plan['status'] = 'ACTIVE'
                plan['updated_at'] = self.now()
                self.store.save_resolution_plan(target, plan)

                s['workflow_state'] = 'PAUSED_WAITING_FOR_HUMAN'
                s['stage'] = 'HUMAN_DECISION_REQUIRED'
                self.store.save_state(s)

                return {
                    'status': 'WAITING_FOR_HUMAN',
                    'artifact_type': target,
                    'blocker_id': blocker_id,
                    'questions': pending,
                }

            if existing and existing.get('status') == 'RESOLVED':
                item['status'] = 'RESOLVED'
                continue
            self.emit(s,'BLOCKER_RESOLUTION_STARTED',f'{item["blocker_id"]} routed backward for Product Definition resolution.',agent_id=','.join(item['agents']),artifact_type=target,blocker_id=item['blocker_id'],details={'route_to':item['agents']})
            try:
                result = self.adapter.generate(
                    system=self._resolution_system(item['agents']),
                    user=self._resolution_prompt(s, target, item, existing),
                )
            except Exception as e:
                ft = self._failure(e)

                return self._block_resolution_failure(
                    s,
                    target,
                    ','.join(item['agents']),
                    ft,
                    {
                        'message': str(e),
                        'blocker_id': item['blocker_id'],
                    },
                )

            schema_errors=[]
            if not isinstance(result,dict): schema_errors=['resolution response must be a JSON object']
            elif Draft202012Validator:
                schema=json.loads(self.resolution_schema.read_text());schema_errors=[e.message for e in Draft202012Validator(schema).iter_errors(result)]
            elif result.get('resolution_status') not in {'RESOLVED','HUMAN_DECISION_REQUIRED'}: schema_errors=['invalid resolution_status']
            if schema_errors:
                return self._block_resolution_failure(
                    s,
                    target,
                    ','.join(item['agents']),
                    'INVALID_MODEL_RESPONSE',
                    {
                        'message': 'Invalid blocker-resolution response',
                        'errors': schema_errors,
                        'blocker_id': item['blocker_id'],
                    },
                )

            rec={'schema_version':'1.0','initiative_id':s['initiative_id'],'session_id':s['session_id'],'artifact_type':target,'blocker_id':item['blocker_id'],'source_finding':item['finding'],'mode':'BACKWARD','agents':item['agents'],'status':result['resolution_status'],'resolution_summary':result.get('resolution_summary'),'authoritative_business_rules':result.get('authoritative_business_rules',[]),'acceptance_intent':result.get('acceptance_intent',[]),'downstream_dependencies':result.get('downstream_dependencies',[]),'evidence_refs':result.get('evidence_refs',[]),'human_decisions':(existing or {}).get('human_decisions',[]),'updated_at':self.now()}
            if result['resolution_status']=='HUMAN_DECISION_REQUIRED':
                questions=result.get('human_decisions') or []
                if not questions:
                    return self._block_resolution_failure(
                        s,
                        target,
                        ','.join(item['agents']),
                        'INVALID_MODEL_RESPONSE',
                        {
                            'message': (
                                'HUMAN_DECISION_REQUIRED '
                                'without human_decisions'
                            ),
                            'blocker_id': item['blocker_id'],
                        },
                    )
                answered={str(d.get('question','')).strip().lower() for d in (existing or {}).get('human_decisions',[])}
                if str(questions[0].get('question', '')).strip().lower() in answered:
                    return self._block_resolution_failure(
                        s,
                        target,
                        ','.join(item['agents']),
                        'INVALID_MODEL_RESPONSE',
                        {
                            'message': (
                                'Resolver repeated an already answered '
                                'human decision instead of incorporating it'
                            ),
                            'blocker_id': item['blocker_id'],
                        },
                    )
                asked_at=self.now();pending=[]
                for q in questions:
                    qid='Q-'+str(uuid.uuid4());pending.append({'question_id':qid,'question':q.get('question'),'blocking':True,'classification':'HUMAN_DECISION','owner':'PRODUCT_OWNER','route_to':['Product Lead / Orchestrator'],'resolution_stage':'BACKWARD_RESOLUTION','reason':q.get('reason'),'recommendation':q.get('recommendation'),'options':q.get('options',[]),'status':'OPEN','asked_at':asked_at,'blocker_id':item['blocker_id'],'artifact_type':target})
                rec['status']='WAITING_FOR_HUMAN';rec['pending_human_decisions']=pending;self.store.save_resolution(target,item['blocker_id'],rec);item['status']='WAITING_FOR_HUMAN';plan['updated_at']=asked_at;self.store.save_resolution_plan(target,plan);s['open_questions']=pending;s['pending_actions']=[{'type':'DECISION_REQUIRED','question_id':q['question_id'],'question':q['question'],'blocker_id':item['blocker_id'],'asked_at':asked_at} for q in pending];s['workflow_state']='PAUSED_WAITING_FOR_HUMAN';s['stage']='HUMAN_DECISION_REQUIRED';s['active_generation']={'artifact_type':target,'agent_id':'product-lead','attempt':None,'failure_type':'HUMAN_DECISION_REQUIRED','blocker_id':item['blocker_id']};self.store.save_state(s);self.emit(s,'INFORMATION_REQUESTED',f'{item["blocker_id"]} requires a Product Owner decision.','BLOCKER',artifact_type=target,blocker_id=item['blocker_id'],details=pending);return {'status':'WAITING_FOR_HUMAN','artifact_type':target,'blocker_id':item['blocker_id'],'questions':pending}
            # Final governance check before accepting AI resolution.
            pending = self._pending_blocker_decisions(
                s, target, blocker_id
            )

            if pending:
                item['status'] = 'WAITING_FOR_HUMAN'
                plan['status'] = 'ACTIVE'
                plan['updated_at'] = self.now()
                self.store.save_resolution_plan(target, plan)

                s['workflow_state'] = 'PAUSED_WAITING_FOR_HUMAN'
                s['stage'] = 'HUMAN_DECISION_REQUIRED'
                self.store.save_state(s)

                return {
                    'status': 'WAITING_FOR_HUMAN',
                    'artifact_type': target,
                    'blocker_id': blocker_id,
                    'questions': pending,
                }

            rec['status'] = 'RESOLVED'
            rec['resolved_at'] = self.now()

            self.store.save_resolution(
                target, blocker_id, rec
            )

            item['status'] = 'RESOLVED'

            self.emit(
                s,
                'BLOCKER_RESOLVED',
                f'{blocker_id} Product Definition gap resolved.',
                artifact_type=target,
                blocker_id=blocker_id,
                details={'agents': item['agents']},
            )
        plan['status']='RESOLVED';plan['resolved_at']=self.now();self.store.save_resolution_plan(target,plan)
        for alert in s.get('open_alerts',[]):
            if alert.get('alert_id')==rw.get('source_alert_id') and not alert.get('resolved'):alert['resolved']=True;alert['resolved_at']=self.now();alert['resolution']='BACKWARD_ORCHESTRATION_COMPLETED';alert['resolved_by']=actor
        resolved=self.store.list_resolutions(target);s.setdefault('rework_feedback',{})[target]={'decision':'BACKWARD_RESOLUTION_COMPLETED','comments':'Product Definition blockers resolved through governed BACKWARD orchestration. Consume product_definition_resolutions from the Agent Context Package.','at':self.now(),'resolution_refs':[r.get('blocker_id') for r in resolved if r.get('status')=='RESOLVED']};s['resolution_workflow']={'status':'RESOLVED','artifact_type':target,'source_alert_id':rw.get('source_alert_id'),'resolved_at':self.now()};s['workflow_state']='READY_TO_RUN';s['stage']='PRODUCT_DEFINITION';s['active_generation']=None;s['open_questions']=[];s['pending_actions']=[];self.store.save_state(s);self.emit(s,'BACKWARD_ORCHESTRATION_COMPLETED',f'{target} Product Definition blockers resolved; returning to Requirements rework.',artifact_type=target,details={'resolution_refs':s['rework_feedback'][target]['resolution_refs']});return {'status':'RESOLVED','artifact_type':target,'resolution_refs':s['rework_feedback'][target]['resolution_refs']}
    def retry_pending_generation(self,s,actor='human',reason='Retry after runtime/context correction'):
        # A generic retry must not bypass mandatory human decisions.
        rw = s.get('resolution_workflow') or {}

        if rw.get('status') == 'ACTIVE':
            target = rw.get('artifact_type')

            if target:
                plan = self.store.load_resolution_plan(target)

                if plan:
                    for item in plan.get('items', []):
                        blocker_id = item.get('blocker_id')

                        if not blocker_id:
                            continue

                        pending = self._pending_blocker_decisions(
                            s, target, blocker_id
                        )

                        if pending:
                            raise ValueError(
                                'Cannot retry while a required human decision '
                                f'remains unanswered for blocker {blocker_id}. '
                                'Record the human decision before resuming.'
                            )
        if rw.get('status') == 'ACTIVE':
            raise ValueError(
                'Cannot use generic retry while a BACKWARD blocker-resolution '
                'workflow is active. Correct the underlying failure and use '
                'resolve-blockers to resume the existing resolution plan.'
            )
        if s.get('pending_approvals'):raise ValueError('Cannot retry while an artifact is awaiting human review')
        stage=s.get('stage');recoverable={'INFORMATION_REQUIRED','HUMAN_DECISION_REQUIRED','QUALITY_BLOCKED','QUALITY_REVIEW_FAILED','PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE','GENERATION_FAILED','INVALID_MODEL_RESPONSE','SCHEMA_VALIDATION_FAILED'}
        if stage not in recoverable:raise ValueError(f'No recoverable blocked generation is available for retry from stage {stage!r}')
        cleared=[]
        if stage in {'INFORMATION_REQUIRED','HUMAN_DECISION_REQUIRED'}:cleared=list(s.get('open_questions',[]));s['open_questions']=[]
        active=s.get('active_generation') or {};target=active.get('artifact_type') or self.next_ready(s)
        for alert in s.get('open_alerts',[]):
            if alert.get('severity')=='BLOCKER' and not alert.get('resolved') and (not target or alert.get('artifact_type') in {None,target}):alert['resolved']=True;alert['resolved_at']=self.now();alert['resolution']='GENERATION_RETRY_REQUESTED';alert['resolution_reason']=reason;alert['resolved_by']=actor
        s['pending_actions']=[];s['workflow_state']='READY_TO_RUN';s['stage']='PRODUCT_DEFINITION';s['active_generation']=None;self.store.save_state(s);self.emit(s,'GENERATION_RETRY_REQUESTED','Targeted blocked generation cleared for retry.','INFO',details={'actor':actor,'reason':reason,'previous_stage':stage,'artifact_type':target,'cleared_questions':cleared});return {'cleared_questions':cleared,'artifact_type':target,'previous_stage':stage}
    def completion(self,s):
        missing=[x for x in s['required_outputs'] if s['artifacts'].get(x,{}).get('status')!='APPROVED'];blockers=[a for a in s.get('open_alerts',[]) if a.get('severity')=='BLOCKER' and not a.get('resolved',False)];final_ok='PRODUCT_REVIEW_REPORT' not in s['required_outputs'] or s.get('final_product_review_passed');return {'complete':not missing and not blockers and not s.get('open_questions') and not s.get('pending_approvals') and final_ok,'missing_or_unapproved':missing,'blockers':blockers,'final_product_review_passed':final_ok}
