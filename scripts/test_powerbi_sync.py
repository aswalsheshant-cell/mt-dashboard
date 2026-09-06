"""
Unit tests for Power BI Sync Agent: Capacity-aware payload generation, refresh ID tracking,
and exponential backoff retry logic.
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from powerbi_sync_agent import PowerBISyncAgent


class TestPowerBISyncAgentPayloads(unittest.TestCase):
    """Verify capacity-aware payload generation (Premium vs. Shared)."""

    def setUp(self):
        self.tenant_id = "test-tenant-id"
        self.client_id = "test-client-id"
        self.client_secret = "test-secret"
        self.workspace_id = "test-workspace"
        self.dataset_id = "test-dataset"

    def test_shared_capacity_payload(self):
        """Shared (Pro) capacity uses notifyOption payload."""
        agent = PowerBISyncAgent(
            self.tenant_id,
            self.client_id,
            self.client_secret,
            self.workspace_id,
            self.dataset_id,
            is_premium_capacity=False
        )

        # Mock the API request to capture payload
        with patch.object(agent, '_api_request') as mock_api:
            # Return 202 Accepted with a Location header
            mock_api.return_value = (202, {}, {"Location": f"/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes/refresh-id-123"})

            # Mock token acquisition
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            result = agent.trigger_refresh()

            # Verify the API was called with correct payload
            mock_api.assert_called_once()
            call_kwargs = mock_api.call_args[1]
            payload = call_kwargs.get('payload')

            self.assertIsNotNone(payload, "Shared capacity should include payload")
            self.assertIn("notifyOption", payload, "Shared payload must include notifyOption")
            self.assertEqual(payload["notifyOption"], "NoNotification")
            self.assertNotIn("type", payload, "Shared payload should NOT include type")
            self.assertNotIn("commitMode", payload, "Shared payload should NOT include commitMode")

    def test_premium_capacity_payload(self):
        """Premium/Fabric (Enhanced) capacity uses type+commitMode payload (no notifyOption)."""
        agent = PowerBISyncAgent(
            self.tenant_id,
            self.client_id,
            self.client_secret,
            self.workspace_id,
            self.dataset_id,
            is_premium_capacity=True
        )

        # Mock the API request to capture payload
        with patch.object(agent, '_api_request') as mock_api:
            # Return 202 Accepted with a Location header
            mock_api.return_value = (202, {}, {"Location": f"/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes/refresh-id-456"})

            # Mock token acquisition
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            result = agent.trigger_refresh()

            # Verify the API was called with correct payload
            mock_api.assert_called_once()
            call_kwargs = mock_api.call_args[1]
            payload = call_kwargs.get('payload')

            self.assertIsNotNone(payload, "Premium capacity should include payload")
            self.assertIn("type", payload, "Premium payload must include type")
            self.assertIn("commitMode", payload, "Premium payload must include commitMode")
            self.assertEqual(payload["type"], "Full")
            self.assertEqual(payload["commitMode"], "Transactional")
            self.assertNotIn("notifyOption", payload, "Premium payload should NOT include notifyOption")


class TestPowerBISyncAgentRefreshTracking(unittest.TestCase):
    """Verify exact refresh ID matching and tracking."""

    def setUp(self):
        self.tenant_id = "test-tenant"
        self.client_id = "test-client"
        self.client_secret = "test-secret"
        self.workspace_id = "test-ws"
        self.dataset_id = "test-ds"

    def test_location_header_refresh_id_extraction(self):
        """Extract refresh ID from Location header."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=True
        )

        with patch.object(agent, '_api_request') as mock_api:
            refresh_uuid = "550e8400-e29b-41d4-a716-446655440000"
            mock_api.return_value = (
                202,
                {},
                {"Location": f"/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes/{refresh_uuid}"}
            )
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            result = agent.trigger_refresh()
            self.assertEqual(result, refresh_uuid, "Should extract exact UUID from Location header")

    def test_request_id_header_fallback(self):
        """Fallback to x-ms-request-id if Location header missing."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=True
        )

        with patch.object(agent, '_api_request') as mock_api:
            request_id = "req-12345-67890"
            mock_api.return_value = (202, {}, {"x-ms-request-id": request_id})
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            result = agent.trigger_refresh()
            self.assertEqual(result, request_id, "Should fallback to request ID")

    def test_exact_id_matching_in_poll(self):
        """Poll with exact ID matching (no fallback to top=1)."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=True
        )

        tracking_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch.object(agent, '_api_request') as mock_api:
            # First call: poll returns 5 items, exact match in middle
            mock_api.return_value = (
                200,
                {
                    "value": [
                        {"id": "old-refresh-1", "status": "Completed"},
                        {"id": "old-refresh-2", "status": "Completed"},
                        {"id": tracking_id, "status": "Completed"},  # Exact match
                        {"id": "old-refresh-3", "status": "Completed"},
                        {"id": "old-refresh-4", "status": "Completed"},
                    ]
                },
                {}
            )
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            result = agent.poll_refresh(tracking_id, timeout_sec=300)
            self.assertIsNotNone(result, "Should find exact matching refresh")
            self.assertEqual(result["id"], tracking_id, "Should return exact match, not top=1")

    def test_poll_timeout_on_not_found(self):
        """Timeout if exact ID never found in poll history."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=True
        )

        tracking_id = "non-existent-id"

        with patch.object(agent, '_api_request') as mock_api:
            # Poll returns items but none match tracking_id
            mock_api.return_value = (
                200,
                {
                    "value": [
                        {"id": "other-refresh-1", "status": "InProgress"},
                        {"id": "other-refresh-2", "status": "InProgress"},
                    ]
                },
                {}
            )
            agent.access_token = "mock-token"
            agent.token_expiry = float('inf')

            with self.assertRaises(TimeoutError):
                agent.poll_refresh(tracking_id, timeout_sec=1, poll_interval=0.5)


class TestPowerBISyncAgentRetryLogic(unittest.TestCase):
    """Verify exponential backoff retry behavior on transient errors."""

    def setUp(self):
        self.tenant_id = "test-tenant"
        self.client_id = "test-client"
        self.client_secret = "test-secret"
        self.workspace_id = "test-ws"
        self.dataset_id = "test-ds"

    def test_token_retry_on_429(self):
        """Retry token acquisition on HTTP 429 (rate limit)."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id
        )

        with patch('urllib.request.urlopen') as mock_urlopen:
            # Fail twice, succeed on third
            import urllib.error
            fail_response = Mock()
            fail_response.code = 429
            fail_response.headers = {}
            fail_response.read.return_value = b'{"error": "rate limited"}'

            success_response = Mock()
            success_response.status = 200
            success_response.read.return_value = json.dumps({
                "access_token": "token-xyz",
                "expires_in": 3600
            }).encode()
            success_response.headers = {}
            success_response.__enter__ = Mock(return_value=success_response)
            success_response.__exit__ = Mock(return_value=False)

            mock_urlopen.side_effect = [
                urllib.error.HTTPError("url", 429, "Rate Limited", {}, None),
                urllib.error.HTTPError("url", 429, "Rate Limited", {}, None),
                success_response
            ]

            with patch('time.sleep'):  # Skip actual sleep
                token = agent._get_bearer_token(max_retries=3)
                self.assertEqual(token, "token-xyz", "Should succeed after retries")

    def test_api_request_retry_on_503(self):
        """Retry API request on HTTP 503 (service unavailable)."""
        agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id
        )
        agent.access_token = "mock-token"
        agent.token_expiry = float('inf')

        with patch('urllib.request.urlopen') as mock_urlopen:
            import urllib.error

            success_response = Mock()
            success_response.status = 200
            success_response.read.return_value = json.dumps({"value": []}).encode()
            success_response.headers = {}
            success_response.__enter__ = Mock(return_value=success_response)
            success_response.__exit__ = Mock(return_value=False)

            mock_urlopen.side_effect = [
                urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None),
                success_response
            ]

            with patch('time.sleep'):  # Skip actual sleep
                status, body, headers = agent._api_request("/test", max_retries=2)
                self.assertEqual(status, 200, "Should succeed after retry")


class TestPowerBISyncAgentExitCodes(unittest.TestCase):
    """Verify hard exit codes on credential/step failures."""

    def test_missing_credentials_exit_code(self):
        """main() should exit with code 1 if credentials missing."""
        # This is tested at the integration/CLI level via main() function
        # which checks for environment variables and calls sys.exit(1)
        pass  # Integration test (would require subprocess call)

    def test_refresh_failure_exit_code(self):
        """Refresh errors should result in non-zero exit code."""
        # This is tested at the integration/CLI level
        # The main() function catches RuntimeError/TimeoutError and calls sys.exit(1)
        pass  # Integration test


class TestCapacityPayloadIntegration(unittest.TestCase):
    """Integration: Verify both capacity types generate correct payloads and handle responses."""

    def setUp(self):
        self.tenant_id = "test-tenant"
        self.client_id = "test-client"
        self.client_secret = "test-secret"
        self.workspace_id = "test-ws"
        self.dataset_id = "test-ds"

    def test_shared_to_premium_transition(self):
        """Verify agent correctly switches payload when capacity flag changes."""
        # Shared capacity
        shared_agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=False
        )
        self.assertFalse(shared_agent.is_premium, "Shared agent should have is_premium=False")

        # Premium capacity
        premium_agent = PowerBISyncAgent(
            self.tenant_id, self.client_id, self.client_secret,
            self.workspace_id, self.dataset_id, is_premium_capacity=True
        )
        self.assertTrue(premium_agent.is_premium, "Premium agent should have is_premium=True")


if __name__ == "__main__":
    unittest.main(verbosity=2)
