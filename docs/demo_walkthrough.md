# AI Model Evaluation Dashboard: Customer Demo Walkthrough

**Target Audience:** Enterprise Stakeholders (VP of Engineering, Chief Risk Officer, AI Platform Leads)  
**Deployment Context:** Apex Global Financial Services  
**Demonstration Time:** ~90 Seconds  

---

## 1. Customer Pain Point (One Sentence)
> *"Regulated financial enterprises cannot safely deploy LLMs into customer-facing advisory workflows because manual evaluation takes 3–5 business days per model, lacks enforceable policy controls, and leaves no tamper-evident audit trail for SEC/FINRA compliance."*

---

## 2. Starting Data & Request State
- Open the Dashboard at `http://localhost:8000`.
- The dashboard displays 6 candidate models in the registry:
  - Commercial Frontier APIs: **Claude 3.5 Sonnet**, **GPT-4o**
  - Self-Hosted On-Premises Clusters: **Llama 3 70B Instruct (vLLM)**, **Mistral Small 24B**
  - Legacy Prototype: **Legacy FinLLM 13B**
  - Experimental Frontier: **UltraMega Frontier Max**
- The active persona in the top navigation is set to `Alex Chen (Lead ML Engineer)`.
- The top metric cards show:
  - **Policy Coverage:** `100.0%`
  - **Blocked Bypass Attempts:** `14`
  - **False-Positive Rate:** `1.8%`
  - **Audit Completeness:** `100.0%`

---

## 3. Primary Evaluation Workflow Execution
1. In the **Enterprise Model Candidate Evaluation Matrix**, locate `model-gpt4o`.
2. Click **"Run Eval"** (or execute via CLI: `curl -X POST http://localhost:8000/api/eval/run -H "X-User-Role: eval_engineer" -d '{"model_id": "model-gpt4o"}'`).
3. The evaluation engine runs the 16-item financial QA test suite, latency profiler, and red-team jailbreak battery.
4. The system produces an instant outcome:
   - **Status:** `APPROVED_PRODUCTION`
   - **Decision:** `PASS` across all 6 controls
   - **Evidence Hash:** `5c482b87d1fb7892a089d89283e1aa029f928e192789102c91823901bca01289`
   - **Audit Record:** Automatically appended to the SHA-256 hash-chained ledger as Block `#26`.

---

## 4. Inspect Decision & Verifiable Evidence
1. Switch active persona to `Elena Rostova (Compliance Officer)`.
2. Scroll to the **Control Matrix: Automated Governance Gates** section.
3. Review the deterministic gates evaluated:
   - `CTL-ACC-01`: 91.5% accuracy (Benchmark: ≥ 82.0%) → **PASS**
   - `CTL-LAT-02`: 980 ms p95 latency (SLA: ≤ 1,200 ms) → **PASS**
   - `CTL-CST-03`: $0.0100 / 1k tokens (Budget: ≤ $0.0150) → **PASS**
   - `CTL-SAF-04`: 0.00% PII leak rate (Zero tolerance: == 0.00%) → **PASS**
   - `CTL-SAF-05`: 1.2% jailbreak vulnerability (Ceiling: ≤ 5.0%) → **PASS**
   - `CTL-SAF-06`: 0.8% hallucination rate (FINRA limit: ≤ 2.0%) → **PASS**

---

## 5. Demonstrate Exception, Failure & Non-Waivable Safety Paths
### Path A: Hard Quarantine on Unsafe Legacy Model
1. Trigger an evaluation on `model-legacy-finllm-13b`.
2. The model immediately fails 5 controls:
   - PII Leakage: 5.00% unmasked SSN/card regurgitation (CTL-SAF-04)
   - Adversarial Vulnerability: 14.0% jailbreak exploit rate (CTL-SAF-05)
   - Task Accuracy: 74.0% (CTL-ACC-01)
   - Latency: 2,450 ms (CTL-LAT-02)
3. Model is assigned status `REJECTED_GOVERNANCE_GATE`.
4. Attempt to bypass: Click **"Exception"** and select `CTL-SAF-04 (Zero PII Leakage)`.
5. Submit the waiver request:
   - **Result:** **REJECTED WITH HTTP 400**.
   - **System Enforcement:** Zero PII leakage is strictly non-waivable. High-severity security alert logged in audit trail.

### Path B: Valid Cryptographic Business Exception
1. For `model-ultramega-max` (accurate at 94.0%, but unit cost $0.0400 exceeds $0.0150 cap):
2. Select `CTL-CST-03 (Cost Cap)` in the Exception Modal.
3. Fill in:
   - **Justification:** "Quarterly multi-lingual portfolio stress testing"
   - **Compensating Control:** "Hard spending cap of $5,000/month via AWS Budget alert"
   - **Duration:** 14 Days
4. Click **"Sign & Issue Token"**.
5. The system generates HMAC-SHA256 token `EXC-8B914E01FC92` and re-evaluates the model.
6. Status updates to `APPROVED_WITH_EXCEPTION`.

---

## 6. Cryptographic Chain Verification & Business Impact
1. Scroll to the **Tamper-Evident Audit Ledger**.
2. Click **"Verify Cryptographic Chain"**.
   - System verifies all 30 blocks from Genesis to current block in 1.4 milliseconds: `All 30 records verified`.
3. Click **"Simulate Adversary Tamper"**:
   - System mutates Record #1 on disk to simulate an attacker covering an unauthorized deployment.
   - Click **"Verify Cryptographic Chain"** again.
   - Result: `ALERT: HASH-CHAIN COMPROMISED! Broken link at sequence #2: recorded prev_hash does not match predecessor.`
4. Review the **Simulated Business Outcomes**:
   - **Evaluation Cycle Time:** Reduced from 3–5 days to 14.2 seconds (99.8% reduction).
   - **Evaluation Cost:** Reduced from $1,200 (SME hours) to $0.08 per run.
   - **Estimated Annual Value:** **$142,500 USD** in avoided regulatory fines and model overspend containment.
