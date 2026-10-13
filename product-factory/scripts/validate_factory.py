#!/usr/bin/env python3
"""Purpose: CI validation of Product Factory YAML/JSON syntax and required integration files."""
from pathlib import Path
import json, sys
try:
 import yaml
except ImportError:
 print("PyYAML is required: pip install pyyaml", file=sys.stderr); sys.exit(2)
root=Path(__file__).resolve().parents[1]
required=["factory.yaml","registry.yaml","TEAM.md","orchestration/orchestration-policy.yaml","orchestration/transitions.yaml","intake/initiative-types.yaml"]
errors=[]
for r in required:
 if not (root/r).exists(): errors.append(f"missing required file: {r}")
for p in root.rglob("*.yaml"):
 try: yaml.safe_load(p.read_text())
 except Exception as e: errors.append(f"YAML {p.relative_to(root)}: {e}")
for p in root.rglob("*.json"):
 try: json.loads(p.read_text())
 except Exception as e: errors.append(f"JSON {p.relative_to(root)}: {e}")
policy=yaml.safe_load((root/'orchestration/orchestration-policy.yaml').read_text())
expected={"FORWARD","BACKWARD","PARALLEL","CONDITIONAL","REWORK","ESCALATION"}
actual=set(policy['orchestration']['supported_modes'])
if actual != expected: errors.append(f"orchestration modes mismatch: {actual}")
init=yaml.safe_load((root/'intake/initiative-types.yaml').read_text())
needed={"NEW_PRODUCT","NEW_CAPABILITY","NEW_FEATURE","PRODUCT_CHANGE","DEFECT"}
if not needed.issubset(init['initiative_types']): errors.append("initiative taxonomy incomplete")
if errors:
 print("VALIDATION FAILED")
 for e in errors: print("-",e)
 sys.exit(1)
print("VALIDATION PASSED")
