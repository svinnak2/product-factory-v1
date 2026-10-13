"""Deterministic adapter for integration tests; never represents production product analysis."""
import re
from .base import ModelAdapter
class MockAdapter(ModelAdapter):
    def generate(self, *, system, user):
        if user.startswith('Independently review this '): return {'pass':True,'findings':[]}
        m=re.search(r'OUTPUT_TYPE:\s*([A-Z_]+)',user); typ=m.group(1) if m else 'UNKNOWN'
        affected=['PRD','REQUIREMENTS'] if typ=='CHANGE_IMPACT_ANALYSIS' else []
        return {'artifact_type':typ,'title':typ.replace('_',' ').title(),'summary':'Deterministic integration-test artifact; not production product analysis.','content':{'test_mode':True,'output_type':typ},'evidence_status':'ASSUMPTION','open_questions':[],'warnings':['MOCK_ADAPTER_OUTPUT'],'traceability':[],'affected_outputs':affected}
