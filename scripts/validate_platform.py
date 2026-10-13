"""Purpose: Validate core AI-PDLC platform structure, YAML/JSON syntax, canonical Product Factory agents and mandatory policy files."""
from pathlib import Path
import json, sys
try:
    import yaml
except ImportError:
    print("PyYAML is required"); sys.exit(2)

ROOT=Path(__file__).resolve().parents[1]
errors=[]
required=[
"product-factory/factory.yaml","product-factory/registry.yaml","contracts/README.md",
"platform/ai-pdlc-factory-topology.yaml","orchestration/PARENT_AI_PDLC_CONTRACT.md",
 "policies/policy-registry.yaml","policies/security-gates.yaml","policies/exception-policy.yaml",
"intake/product-initiative.schema.json","human-interface/interaction-protocol.yaml",
"product-factory/orchestration/human-interaction-policy.yaml",
"product-factory/orchestration/approval-gates.yaml",
"product-factory/orchestration/artifact-lifecycle.yaml",
"product-factory/orchestration/checkpoint-policy.yaml",
"product-factory/orchestration/development-context-policy.yaml",
"cli/ai_pdlc.py",
"runtime/orchestrator/product.py","runtime/adapters/base.py","runtime/adapters/openai_compatible.py",
"runtime/stores/local.py","runtime/adapters/codex.py","product-factory/orchestration/output-catalog.yaml","product-factory/orchestration/quality-standards.yaml",
"product-factory/orchestration/completion-profiles.yaml","product-factory/schemas/executable-artifact.schema.json",
"tests/test_runtime_smoke.py","tests/test_runtime_v61.py"
]
agents=["product-lead","product-discovery","requirements","workflow-journey","ai-product-strategy","product-analytics","product-review-routing"]
for r in required:
    if not (ROOT/r).exists(): errors.append(f"Missing {r}")
for a in agents:
    for f in ["AGENT.md","SKILLS.md"]:
        if not (ROOT/"product-factory"/"agents"/a/f).exists(): errors.append(f"Missing agent file {a}/{f}")
for p in ROOT.rglob("*.yaml"):
    try: yaml.safe_load(p.read_text())
    except Exception as e: errors.append(f"YAML {p.relative_to(ROOT)}: {e}")
for p in ROOT.rglob("*.json"):
    try: json.loads(p.read_text())
    except Exception as e: errors.append(f"JSON {p.relative_to(ROOT)}: {e}")
if errors:
    print("VALIDATION FAILED")
    for e in errors: print("-",e)
    sys.exit(1)
print("VALIDATION PASSED")
