"""Tamper-evident, hash-chained audit ledger service."""
import hmac
import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from app.config import settings
from app.models.domain import AuditRecord
from app.audit.hasher import canonical_json_dumps, compute_sha256
from app.security.redaction import sanitize_payload


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class AuditLedger:
    """Thread-safe append-only audit ledger with cryptographic hash chaining and HMAC integrity."""

    def __init__(self, ledger_path: Optional[Path] = None, hmac_key: Optional[str] = None):
        self.ledger_path = ledger_path or settings.AUDIT_LEDGER_PATH
        self.hmac_key = (hmac_key or settings.AUDIT_HMAC_KEY).encode("utf-8")
        self._lock = threading.Lock()
        self._records: List[AuditRecord] = []
        self._init_ledger()

    def _init_ledger(self) -> None:
        """Initialize or reload ledger from disk."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if self.ledger_path.exists():
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            record = AuditRecord(**data)
                            self._records.append(record)
                        except Exception:
                            pass

    def _compute_record_hash(self, record: AuditRecord) -> str:
        """Compute the deterministic digest of an audit record."""
        payload = {
            "sequence_id": record.sequence_id,
            "timestamp": record.timestamp,
            "actor": record.actor,
            "role": record.role,
            "action": record.action,
            "resource": record.resource,
            "result": record.result,
            "reason": record.reason,
            "correlation_id": record.correlation_id,
            "payload_hash": record.payload_hash,
            "prev_hash": record.prev_hash,
        }
        return compute_sha256(payload)

    def _compute_hmac(self, record_hash: str) -> str:
        """Compute HMAC-SHA256 for record authenticity."""
        return hmac.new(self.hmac_key, record_hash.encode("utf-8"), hashlib.sha256).hexdigest()

    def append(
        self,
        actor: str,
        role: str,
        action: str,
        resource: str,
        result: str,
        reason: str,
        correlation_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Append an immutable audit entry to the ledger with hash chaining."""
        with self._lock:
            # 1. Sanitize payload to guarantee no PII or raw credentials enter audit records
            sanitized_payload = sanitize_payload(payload or {})
            payload_hash = compute_sha256(sanitized_payload)

            # 2. Determine sequence ID and previous hash
            if not self._records:
                seq_id = 1
                prev_hash = GENESIS_HASH
            else:
                last_rec = self._records[-1]
                seq_id = last_rec.sequence_id + 1
                prev_hash = self._compute_record_hash(last_rec)

            timestamp = datetime.now(timezone.utc).isoformat()

            # 3. Form un-signed record
            record = AuditRecord(
                sequence_id=seq_id,
                timestamp=timestamp,
                actor=actor,
                role=role,
                action=action,
                resource=resource,
                result=result,
                reason=reason,
                correlation_id=correlation_id,
                payload_hash=payload_hash,
                prev_hash=prev_hash,
                hmac_signature="",
                details=sanitized_payload if sanitized_payload else None,
            )

            # 4. Compute record hash & HMAC signature
            record_hash = self._compute_record_hash(record)
            record.hmac_signature = self._compute_hmac(record_hash)

            # 5. Append in-memory and write to disk
            self._records.append(record)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")

            return record

    def list_records(self, limit: int = 100, offset: int = 0) -> List[AuditRecord]:
        """List audit records in descending chronological order."""
        with self._lock:
            reversed_records = list(reversed(self._records))
            return reversed_records[offset : offset + limit]

    def count(self) -> int:
        """Total number of audit records."""
        with self._lock:
            return len(self._records)

    def verify_integrity(self) -> Tuple[bool, str, Optional[int]]:
        """
        Verify cryptographic hash-chain continuity and HMAC authenticity across all entries.
        Returns: (is_valid, message, broken_sequence_id)
        """
        with self._lock:
            if not self._records:
                return True, "Audit ledger is empty (genesis state verified).", None

            expected_prev_hash = GENESIS_HASH

            for idx, rec in enumerate(self._records):
                # 1. Verify sequence order
                expected_seq = idx + 1
                if rec.sequence_id != expected_seq:
                    return (
                        False,
                        f"Sequence gap detected: expected {expected_seq}, found {rec.sequence_id}.",
                        rec.sequence_id,
                    )

                # 2. Verify hash chain link
                if rec.prev_hash != expected_prev_hash:
                    return (
                        False,
                        f"Hash chain broken at record #{rec.sequence_id}: recorded prev_hash '{rec.prev_hash}' does not match computed predecessor hash '{expected_prev_hash}'.",
                        rec.sequence_id,
                    )

                # 3. Verify HMAC signature
                rec_hash = self._compute_record_hash(rec)
                expected_hmac = self._compute_hmac(rec_hash)
                if not hmac.compare_digest(rec.hmac_signature, expected_hmac):
                    return (
                        False,
                        f"HMAC signature invalid at record #{rec.sequence_id}. Possible unauthorized record modification.",
                        rec.sequence_id,
                    )

                # Step forward
                expected_prev_hash = rec_hash

            return True, f"All {len(self._records)} audit ledger entries cryptographically verified.", None

    def simulate_tamper(self, sequence_id: int) -> bool:
        """Test helper to simulate adversary altering an audit log entry on disk."""
        with self._lock:
            for rec in self._records:
                if rec.sequence_id == sequence_id:
                    # Tamper in memory
                    rec.result = "TAMPERED_ALLOWED"
                    rec.reason = "Illegitimately modified by simulated attacker"
                    # Rewrite disk to reflect tamper
                    with open(self.ledger_path, "w", encoding="utf-8") as f:
                        for r in self._records:
                            f.write(r.model_dump_json() + "\n")
                    return True
            return False


# Global ledger instance
audit_ledger = AuditLedger()
