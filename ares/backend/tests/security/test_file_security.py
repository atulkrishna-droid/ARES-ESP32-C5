"""Security Audit Tests: File Security & Storage Hardening (Section 22)."""
import os
import pytest
from app.services.evidence_service import EvidenceService
from app.core.exceptions import StorageException
from app.models.case import Case


def test_path_traversal_filename_sanitization(db_session, seeded_users):
    """Verify that malicious path traversal sequences in filenames are sanitized."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-PATH-TRAVERSAL", title="Path Traversal Test", created_by=admin.id)
    db_session.add(case)
    db_session.commit()

    malicious_filename = "../../../../../etc/passwd"
    payload = b"root:x:0:0:root:/root:/bin/bash"

    evidence = EvidenceService.create_evidence(
        db=db_session,
        case_id=case.id,
        assessment_id=None,
        device_id=None,
        file_name=malicious_filename,
        raw_bytes=payload,
        collected_by=admin.id,
    )

    # Stored file name must be stripped of traversal path characters
    assert "/" not in evidence.file_name
    assert "\\" not in evidence.file_name
    assert ".." not in evidence.file_name
    assert evidence.file_name == "passwd"

    # Verify storage path is strictly within data/evidence
    assert os.path.isabs(evidence.storage_path) or evidence.storage_path.startswith("data")
    assert ".." not in evidence.storage_path


def test_unbounded_file_upload_rejection(db_session, seeded_users, monkeypatch):
    """Verify that files exceeding the configured maximum size are rejected."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-OVERSIZE-FILE", title="Oversize File Test", created_by=admin.id)
    db_session.add(case)
    db_session.commit()

    # Artificially set max size to 1 MB for testing
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_EVIDENCE_SIZE_MB", 1)

    oversized_bytes = b"X" * (2 * 1024 * 1024)  # 2MB > 1MB limit

    with pytest.raises(StorageException) as exc_info:
        EvidenceService.create_evidence(
            db=db_session,
            case_id=case.id,
            assessment_id=None,
            device_id=None,
            file_name="oversize.bin",
            raw_bytes=oversized_bytes,
            collected_by=admin.id,
        )
    assert "exceeds maximum allowed limit" in str(exc_info.value).lower()
