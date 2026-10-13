"""Smoke tests for product-agnostic executable orchestration."""
from pathlib import Path
import sys, tempfile, yaml
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from runtime.stores.local import LocalStore
from runtime.adapters.mock import MockAdapter
from runtime.orchestrator.product import ProductOrchestrator
def run_example(name):
    with tempfile.TemporaryDirectory() as d:
        st=LocalStore(d); o=ProductOrchestrator(ROOT,st,MockAdapter())
        init=yaml.safe_load((ROOT/"intake/examples"/name).read_text()); s=o.start(init)
        a=o.generate_next(s); assert a is not None; assert a["status"]=="HUMAN_REVIEW_REQUIRED"
        s=st.load_state(s["initiative_id"]); assert s["workflow_state"]=="PAUSED_WAITING_FOR_HUMAN"
        o.decide(s,"APPROVED"); s=st.load_state(s["initiative_id"]); assert s["workflow_state"]=="RUNNING"
def test_medical(): run_example("medical-appeals.yaml")
def test_consumer(): run_example("consumer-event-planner.yaml")
def test_evolution(): run_example("inventory-feature-evolution.yaml")
if __name__=="__main__":
    test_medical(); test_consumer(); test_evolution(); print("RUNTIME SMOKE TESTS PASSED")
