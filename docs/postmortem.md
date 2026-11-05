# Incident Postmortem: Schema Validation Precedence on Exception Tokens

**Incident Identifier:** INC-20261105-01  
**Severity:** Low (Internal Development / Smoke Test Phase)  
**Date:** 2026-11-05  
**Service:** AI Model Governance Gateway (`/api/policies/exceptions`)  
**FDE Lead:** Forward Deployed Engineering  

---

## 1. Executive Summary
During initial deployment verification using `scripts/smoke_test.py`, test case #6 (*Zero-Tolerance Exception Block on PII Leakage*) returned `HTTP 422 Unprocessable Entity` rather than the anticipated `HTTP 400 Bad Request`.

While the system remained secure and failed closed (no invalid exception token was issued), the unexpected HTTP status revealed that Pydantic input layer validation was masking downstream security and policy assertions.

---

## 2. Root Cause Analysis (5 Whys)

1. **Why did the smoke test report a failure?**  
   The test expected an `HTTP 400 Bad Request` indicating that rule `CTL-SAF-04` has zero tolerance and cannot be waived, but received an `HTTP 422 Unprocessable Entity`.

2. **Why was HTTP 422 returned?**  
   FastAPI's Pydantic deserializer rejected the request body before the endpoint handler was invoked.

3. **Why did Pydantic reject the request body?**  
   The test fixture passed `compensating_control: "None"`, which contains 4 characters. The schema definition in `app/models/schemas.py` specified `min_length=10`.

4. **Why was `min_length=10` enforced on compensating control?**  
   Enterprise policy requires non-trivial justification and explicit compensating controls for waivers; trivial single-word strings like `"None"` or `"N/A"` are prohibited.

5. **What was the architectural implication?**  
   The input validation layer correctly rejected low-quality input, but test fixtures and client error handling needed alignment so that policy gate violations (`HTTP 400`) and schema validation failures (`HTTP 422`) are clearly differentiated in API contracts.

---

## 3. Remediation & Fixes Applied

1. **Test Fixture Hardening:**  
   Updated `scripts/smoke_test.py` to supply fully qualified justification and compensating control descriptions (`"Compensating control: firewall logging enabled"`).
2. **Schema & Policy Layer Separation:**  
   Verified that requests satisfying Pydantic schema constraints properly route to `generate_exception_token()`, where zero-tolerance rules (`CTL-SAF-04`) fail closed deterministically with `HTTP 400` and trigger a security audit entry.
3. **Regression Test Addition:**  
   Added unit test `test_zero_tolerance_exception_prohibited` in `tests/test_adversarial_negative.py` to safeguard against status code drift in future releases.

---

## 4. Lessons Learned
- **Fail-Closed Verification:** Even when tests fail, ensuring the system fails *safe* (rejecting the request rather than granting permission) is the paramount property of a zero-trust architecture.
- **Contract Clarity:** Always distinguish between structural validation errors (`422`) and semantic business/governance policy violations (`400`).
