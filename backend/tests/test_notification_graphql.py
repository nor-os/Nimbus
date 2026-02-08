"""
Overview: Tests for notification GraphQL types, converters, and activity dataclasses.
Architecture: Unit tests for GraphQL notification layer (Section 7.2)
Dependencies: pytest, app.api.graphql.types.notification, app.workflows.activities.notification
Concepts: GraphQL types, data conversion, Temporal activity inputs/outputs
"""

from app.workflows.activities.notification import (
    SendEmailInput,
    SendEmailResult,
    SendWebhookBatchInput,
    SendWebhookBatchResult,
    WebhookDeliveryResult,
    WebhookTarget,
    _apply_auth_headers,
)


class TestSendEmailDataclasses:
    """Test email activity dataclasses."""

    def test_send_email_input(self):
        inp = SendEmailInput(
            to_email="user@example.com",
            subject="Test Subject",
            body="Test Body",
        )
        assert inp.to_email == "user@example.com"
        assert inp.from_email == "noreply@nimbus.local"
        assert inp.from_name == "Nimbus"

    def test_send_email_result_success(self):
        result = SendEmailResult(success=True)
        assert result.success is True
        assert result.error is None

    def test_send_email_result_failure(self):
        result = SendEmailResult(success=False, error="SMTP timeout")
        assert result.success is False
        assert result.error == "SMTP timeout"


class TestWebhookActivityDataclasses:
    """Test webhook activity dataclasses."""

    def test_webhook_target_defaults(self):
        target = WebhookTarget(url="https://example.com/hook")
        assert target.auth_type == "NONE"
        assert target.auth_config is None
        assert target.secret is None

    def test_send_webhook_batch_input(self):
        target = WebhookTarget(
            url="https://example.com/hook",
            auth_type="BEARER",
            auth_config={"token": "abc123"},
        )
        inp = SendWebhookBatchInput(
            delivery_ids=["id-1", "id-2"],
            target=target,
            payloads=[{"event": "test1"}, {"event": "test2"}],
        )
        assert len(inp.delivery_ids) == 2
        assert inp.target.auth_type == "BEARER"

    def test_webhook_delivery_result(self):
        result = WebhookDeliveryResult(
            delivery_id="id-1",
            success=True,
            status_code=200,
        )
        assert result.success is True
        assert result.status_code == 200
        assert result.error is None

    def test_send_webhook_batch_result(self):
        results = [
            WebhookDeliveryResult(delivery_id="1", success=True, status_code=200),
            WebhookDeliveryResult(delivery_id="2", success=False, error="timeout"),
        ]
        batch_result = SendWebhookBatchResult(results=results)
        assert len(batch_result.results) == 2
        assert batch_result.results[0].success is True
        assert batch_result.results[1].success is False


class TestApplyAuthHeaders:
    """Test webhook authentication header application."""

    def test_no_auth(self):
        headers = {"Content-Type": "application/json"}
        target = WebhookTarget(url="https://example.com", auth_type="NONE")
        _apply_auth_headers(headers, target)
        assert "Authorization" not in headers

    def test_api_key_auth(self):
        headers = {"Content-Type": "application/json"}
        target = WebhookTarget(
            url="https://example.com",
            auth_type="API_KEY",
            auth_config={"header_name": "X-API-Key", "api_key": "my-secret-key"},
        )
        _apply_auth_headers(headers, target)
        assert headers["X-API-Key"] == "my-secret-key"

    def test_api_key_auth_default_header(self):
        headers = {}
        target = WebhookTarget(
            url="https://example.com",
            auth_type="API_KEY",
            auth_config={"api_key": "secret"},
        )
        _apply_auth_headers(headers, target)
        assert headers["X-API-Key"] == "secret"

    def test_basic_auth(self):
        import base64

        headers = {}
        target = WebhookTarget(
            url="https://example.com",
            auth_type="BASIC",
            auth_config={"username": "user", "password": "pass"},
        )
        _apply_auth_headers(headers, target)
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_bearer_auth(self):
        headers = {}
        target = WebhookTarget(
            url="https://example.com",
            auth_type="BEARER",
            auth_config={"token": "jwt-token-123"},
        )
        _apply_auth_headers(headers, target)
        assert headers["Authorization"] == "Bearer jwt-token-123"

    def test_no_auth_config_does_nothing(self):
        headers = {}
        target = WebhookTarget(
            url="https://example.com",
            auth_type="BEARER",
            auth_config=None,
        )
        _apply_auth_headers(headers, target)
        assert "Authorization" not in headers
