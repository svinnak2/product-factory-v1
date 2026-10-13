from pathlib import Path
import json
try: from jsonschema import Draft202012Validator
except ImportError: Draft202012Validator=None
def validate_artifact(a,schema_path=None,expected_type=None):
    errors=[]
    if Draft202012Validator and schema_path:
        schema=json.loads(Path(schema_path).read_text()); errors += [e.message for e in Draft202012Validator(schema).iter_errors(a)]
    else:
        errors += [f'missing {x}' for x in ['artifact_type','title','summary','content','evidence_status','open_questions'] if x not in a]
    if expected_type and a.get('artifact_type')!=expected_type: errors.append(f'artifact_type must be {expected_type}')
    return sorted(set(errors))
