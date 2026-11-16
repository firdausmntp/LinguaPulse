"""Security boundaries that must hold without external services."""
import time
import unittest
from unittest.mock import patch

from backend import security


class SecurityTests(unittest.TestCase):
    def test_strict_mode_rejects_local_token(self):
        with patch.object(security, "CF_ENFORCE_STRICT", True), \
             patch("backend.security.urllib.request.urlopen", side_effect=OSError("offline")):
            self.assertFalse(security.verify_cf_challenge("CF-LOCAL-PASS-forged")["verified"])
            self.assertFalse(security.verify_cf_challenge("")["verified"])

    def test_unknown_or_expired_handshake_is_rejected(self):
        envelope = {"handshake_id": "missing", "ciphertext": "", "timestamp": int(time.time())}
        with self.assertRaises(ValueError):
            security.decrypt_and_verify_payload(envelope)
        with patch.dict(security.ACTIVE_HANDSHAKES, {"expired": {"issued_at": time.time() - 7201, "session_key": "x"}}):
            with self.assertRaises(ValueError):
                security.decrypt_and_verify_payload({**envelope, "handshake_id": "expired"})


if __name__ == "__main__":
    unittest.main()
