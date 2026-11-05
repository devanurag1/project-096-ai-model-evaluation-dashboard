"""Seed script to pre-populate demonstration models, evaluation runs, and verifiable audit records."""
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.audit.ledger import audit_ledger
from app.services.eval_service import eval_service


def seed_all():
    print("Seeding demo data for AI Model Evaluation Dashboard...")

    # Run evaluations on key models
    models_to_eval = [
        "model-gpt4o",
        "model-claude-sonnet",
        "model-llama3-70b",
        "model-mistral-small",
        "model-legacy-finllm-13b",
        "model-ultramega-max",
    ]

    for mid in models_to_eval:
        try:
            print(f"  -> Evaluating {mid}...")
            run = eval_service.run_evaluation(
                model_id=mid,
                evaluator_id="alex.chen@apexglobal.com",
                evaluator_role="eval_engineer",
                correlation_id=f"SEED-{uuid.uuid4().hex[:8].upper()}",
            )
            print(f"     Status: {run.status} | Overall: {run.policy_summary.overall_status}")
        except Exception as e:
            print(f"     Error evaluating {mid}: {e}")

    # Verify ledger integrity
    is_valid, msg, _ = audit_ledger.verify_integrity()
    print(f"Audit ledger seeded with {audit_ledger.count()} entries. Integrity verified: {is_valid} ({msg})")


if __name__ == "__main__":
    seed_all()
