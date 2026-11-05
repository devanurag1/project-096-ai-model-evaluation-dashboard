# System Architecture: AI Model Evaluation Dashboard

**Customer Deployment:** Apex Global Financial Services  
**Document Version:** 1.0.0  
**Domain:** Regulated Enterprise AI Governance (FINRA / SEC / PCI-DSS / GLBA)  

---

## 1. Architectural Overview

The AI Model Evaluation Dashboard is designed as a **fail-closed, zero-trust governance gateway** that evaluates candidate Large Language Models (LLMs) across four foundational enterprise pillars:
1. **Accuracy (Domain Correctness):** Task precision and recall on mortgage qualification, disclosure requirements, and fee schedules.
2. **Latency (Operational SLA):** p50, p95, and p99 percentile adherence against real-time conversational thresholds (p95 ≤ 1,200 ms).
3. **Cost (Unit Economics):** Blended prompt/completion cost per 1k tokens capped at enterprise budget ceilings ($0.015 / 1k tokens).
4. **Safety & Policy Guardrails:** Real-time red-teaming against prompt injections, DAN jailbreaks, hallucinated financial commitments, and zero-tolerance PII/PCI-DSS leakage.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        1. CLIENT & ACCESS LAYER                        │
│                                                                        │
│  [Business Viewer]    [ML Lead Engineer]   [Compliance]    [SecOps]    │
│           │                   │                 │              │       │
│           ▼                   ▼                 ▼              ▼       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Dashboard SPA & REST API Gateway (Least-Privilege RBAC)  │  │
│  │ - Header Identity Resolution (`X-User-Role`, Bearer JWT)        │  │
│  │ - Traceability Middleware (`X-Correlation-ID`, Latency Tracker) │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  2. POLICY ENFORCEMENT & EVALUATION ENGINE             │
│                                                                        │
│  ┌────────────────────────┐         ┌────────────────────────────────┐ │
│  │ Benchmark Suite Runner │         │ Red-Team & PII Leakage Scanner │ │
│  │ (Financial QA v1.4)    │         │ (Jailbreaks, PANs, SSNs)       │ │
│  └───────────┬────────────┘         └───────────────┬────────────────┘ │
│              │                                      │                  │
│              ▼                                      ▼                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ Policy Engine (Deterministic Control Matrix Evaluation)           │ │
│  │ - CTL-ACC-01: Accuracy >= 82.0%                                   │ │
│  │ - CTL-LAT-02: p95 Latency <= 1,200ms                              │ │
│  │ - CTL-CST-03: Blended Cost <= $0.015/1k tokens                    │ │
│  │ - CTL-SAF-04: Zero PII Leakage (Strict Zero-Tolerance)            │ │
│  │ - CTL-SAF-05: Adversarial Vulnerability <= 5.0%                   │ │
│  │ - CTL-SAF-06: Hallucination Rate <= 2.0%                          │ │
│  └──────────────────┬───────────────────────────────┬────────────────┘ │
│                     │                               │                  │
│                     ▼                               ▼                  │
│  ┌─────────────────────────────────────┐  ┌──────────────────────────┐ │
│  │ Cryptographic Exception Evaluator   │  │ Model Inference Adapters │ │
│  │ - HMAC-SHA256 Token Verification    │  │ - OpenAI Commercial     │ │
│  │ - Non-waivable Zero-Tolerance Check │  │ - Anthropic Commercial   │ │
│  │ - Expiration TTL Enforcement        │  │ - Private vLLM Cluster   │ │
│  └─────────────────────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                3. TAMPER-EVIDENT CRYPTOGRAPHIC AUDIT LEDGER            │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Append-Only SHA-256 Hash Chained Records                         │  │
│  │ [Record #1] ──> [Record #2] ──> [Record #3] ──> ... ──> [Record #N]│  │
│  │ Hash(N) = SHA256(Seq, Actor, Action, Resource, Result, H(N-1))   │  │
│  │ Signature = HMAC-SHA256(Hash(N), System_HMAC_Key)                │  │
│  │ Redaction Engine: All PII/Tokens masked before write to disk      │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Continuous Chain Verification Endpoint (`/api/audit/verify`)     │  │
│  │ - Verifies 100% of sequential links from Genesis to latest block │  │
│  │ - Instant breach detection if any byte is altered in storage     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Security & Design Principles

### 2.1 Fail-Closed Defaults
If an evaluation test experiences a network timeout, malformed payload, missing benchmark metric, or NaN value, the policy engine defaults to `PolicyStatus.FAIL`. Models are never approved or promoted to production due to missing data.

### 2.2 Least-Privilege Role-Based Access Control (RBAC)
All actions are gated behind granular permission checks:
- `business_user`: Read-only access to dashboards, model comparisons, and high-level scorecards. Lacks permission to execute evaluation runs or inspect raw audit trails.
- `eval_engineer`: Authorized to register models, upload benchmark datasets, and execute evaluation runs. Restricted from granting compliance exceptions.
- `compliance_officer`: Authorized to configure policy thresholds, issue cryptographically signed exception tokens, and review audit ledgers.
- `secops_admin`: Full administrative control, including quarantine triggers and ledger export.

### 2.3 Non-Waivable Zero Tolerance
While operational thresholds (such as unit cost or latency) allow cryptographically signed business exceptions (e.g., when a quant research group funds an expensive model), compliance rule **CTL-SAF-04 (Zero PII/Cardholder Leakage)** is hardcoded as non-waivable. Any attempt to issue an exception token for CTL-SAF-04 fails closed with `HTTP 400 Bad Request` and logs a high-severity security incident.

### 2.4 Cryptographic Hash Chaining & Tamper Detection
Audit entries are linked sequentially via SHA-256 hashes (`prev_hash` points to predecessor's digest). Each record is signed with a system HMAC key. Any retroactive modification to historical records breaks the hash chain at the target sequence and invalidates all subsequent blocks.
