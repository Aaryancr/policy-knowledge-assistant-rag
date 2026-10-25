"""Tests for structured JSON logging and sensitive data redaction."""

import json
import logging
from app.core.logging import JSONFormatter


def test_json_formatter_redacts_sensitive_keys():
    formatter = JSONFormatter()
    logger = logging.getLogger("test_redaction")
    record = logger.makeRecord(
        name="test_logger",
        level=logging.INFO,
        fn="test_file.py",
        lno=42,
        msg="User authentication attempt",
        args=(),
        exc_info=None,
        extra={
            "user_email": "admin@example.com",
            "password": "SuperSecretPassword123!",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "api_key": "sk-1234567890abcdef",
            "nested_auth": {
                "secret_key": "hidden_secret",
                "safe_info": "visible_info",
            },
        },
    )

    formatted_output = formatter.format(record)
    parsed = json.loads(formatted_output)

    assert parsed["message"] == "User authentication attempt"
    assert parsed["level"] == "INFO"
    assert parsed["extra"]["user_email"] == "admin@example.com"
    assert parsed["extra"]["password"] == "[REDACTED]"
    assert parsed["extra"]["access_token"] == "[REDACTED]"
    assert parsed["extra"]["api_key"] == "[REDACTED]"
    assert parsed["extra"]["nested_auth"]["secret_key"] == "[REDACTED]"
    assert parsed["extra"]["nested_auth"]["safe_info"] == "visible_info"


def test_json_formatter_truncates_oversized_payloads():
    formatter = JSONFormatter()
    logger = logging.getLogger("test_truncation")
    giant_content = "A" * 2000
    record = logger.makeRecord(
        name="test_logger",
        level=logging.INFO,
        fn="test_file.py",
        lno=10,
        msg="Processing document",
        args=(),
        exc_info=None,
        extra={"document_content": giant_content},
    )

    formatted_output = formatter.format(record)
    parsed = json.loads(formatted_output)

    assert len(parsed["extra"]["document_content"]) < 1050
    assert parsed["extra"]["document_content"].endswith("...")
