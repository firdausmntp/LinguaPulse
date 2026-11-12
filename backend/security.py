import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, Tuple

# Kunci rahasia server (dapat di-override lewat environment variable)
SERVER_MASTER_SECRET = os.environ.get(
    "TOEFL_SERVER_SECRET",
    "linguapulse-toefl-telemetry-secret-key-2026-untirta"
)

# Cloudflare Turnstile Keys (Default menggunakan Cloudflare Official Dummy Test Key untuk localhost)
CF_TURNSTILE_SITEKEY = os.environ.get("CF_TURNSTILE_SITEKEY", "1x00000000000000000000AA")
CF_TURNSTILE_SECRET = os.environ.get("CF_TURNSTILE_SECRET", "1x0000000000000000000000000000000AA")
CF_ENFORCE_STRICT = os.environ.get("CF_ENFORCE_STRICT", "false").lower() == "true"

# Penyimpanan sesi kunci sementara di memori server
ACTIVE_HANDSHAKES: Dict[str, Dict[str, Any]] = {}


def create_security_handshake() -> Dict[str, Any]:
    """Membuat sesi kriptografi (session_id, client_key, nonce) dan konfigurasi Cloudflare Turnstile."""
    handshake_id = "HS-" + secrets.token_hex(8)
    session_key = secrets.token_hex(16)
    issued_at = int(time.time())

    ACTIVE_HANDSHAKES[handshake_id] = {
        "session_key": session_key,
        "issued_at": issued_at,
    }

    # Bersihkan handshake lama (> 2 jam)
    cutoff = issued_at - 7200
    expired = [k for k, v in ACTIVE_HANDSHAKES.items() if v["issued_at"] < cutoff]
    for k in expired:
        ACTIVE_HANDSHAKES.pop(k, None)

    return {
        "handshake_id": handshake_id,
        "session_key": session_key,
        "issued_at": issued_at,
        "encryption_scheme": "SHA256-CTR-HMAC",
        "cf_turnstile_sitekey": CF_TURNSTILE_SITEKEY,
    }


def _keystream_xor(data_bytes: bytes, key_str: str, iv_hex: str) -> bytes:
    """Stream cipher berbasis SHA-256 Counter Mode (CTR) yang kompatibel penuh dengan Web Crypto / JS."""
    out = bytearray(len(data_bytes))
    key_bytes = key_str.encode("utf-8")
    iv_bytes = iv_hex.encode("utf-8")
    block_Count = (len(data_bytes) + 31) // 32

    for counter in range(block_Count):
        ctr_bytes = counter.to_bytes(4, byteorder="big")
        digest = hashlib.sha256(key_bytes + b":" + iv_bytes + b":" + ctr_bytes).digest()
        start = counter * 32
        end = min(start + 32, len(data_bytes))
        for i in range(start, end):
            out[i] = data_bytes[i] ^ digest[i - start]
    return bytes(out)


def decrypt_and_verify_payload(envelope: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Memverifikasi tanda tangan HMAC-SHA256, anti-replay timestamp, dan mendekripsi payload telemetri.
    Jika payload belum terenkripsi (mode legacy/debug), tetap ditangani dengan penanda khusus.
    """
    if "ciphertext" not in envelope:
        return envelope, {"encrypted": False, "hmac_verified": False, "scheme": "PLAINTEXT_FALLBACK"}

    handshake_id = envelope.get("handshake_id", "")
    iv_hex = envelope.get("iv", "")
    ciphertext_b64 = envelope.get("ciphertext", "")
    signature_hex = envelope.get("signature", "")
    timestamp = int(envelope.get("timestamp", 0))

    hs = ACTIVE_HANDSHAKES.get(handshake_id)
    session_key = hs["session_key"] if hs else SERVER_MASTER_SECRET

    # 1. Verifikasi Anti-Replay Timestamp (maksimal selisih 15 menit)
    now = int(time.time())
    if abs(now - timestamp) > 900:
        raise ValueError("Timestamp paket telemetri kedaluwarsa (anti-replay protection).")

    # 2. Verifikasi Integritas HMAC-SHA256 (mencegah manipulasi fitur telemetri di DevTools)
    mac_message = f"{handshake_id}.{iv_hex}.{timestamp}.{ciphertext_b64}".encode("utf-8")
    expected_sig = hmac.new(session_key.encode("utf-8"), mac_message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature_hex):
        raise ValueError("Signature HMAC-SHA256 tidak valid (indikasi manipulasi payload).")

    # 3. Dekripsi Ciphertext (Base64 -> XOR SHA256-CTR -> UTF-8 JSON)
    cipher_bytes = base64.b64decode(ciphertext_b64)
    plain_bytes = _keystream_xor(cipher_bytes, session_key, iv_hex)
    decrypted_dict = json.loads(plain_bytes.decode("utf-8"))

    security_meta = {
        "encrypted": True,
        "hmac_verified": True,
        "scheme": "SHA256-CTR + HMAC-SHA256",
        "cipher_size_bytes": len(cipher_bytes),
    }
    return decrypted_dict, security_meta


def verify_cf_challenge(token: str, remote_ip: str = "127.0.0.1") -> Dict[str, Any]:
    """
    Memverifikasi token Cloudflare Turnstile / Challenge melalui endpoint resmi siteverify.
    """
    if not token:
        if not CF_ENFORCE_STRICT:
            return {"verified": True, "mode": "LOCAL_DEV_BYPASS"}
        return {"verified": False, "error": "Token Cloudflare Challenge tidak ditemukan."}

    # Token simulasi lokal apabila offline
    if token.startswith("CF-LOCAL-PASS-"):
        return {"verified": True, "mode": "CF_LOCAL_CHALLENGE_PASS"}

    try:
        form_data = urllib.parse.urlencode({
            "secret": CF_TURNSTILE_SECRET,
            "response": token,
            "remoteip": remote_ip,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "verified": bool(result.get("success", False)),
                "mode": "CLOUDFLARE_SITEVERIFY_API",
                "hostname": result.get("hostname", "localhost"),
            }
    except Exception:
        # Jika sedang offline di lokal, izinkan selama bukan mode strict production
        return {"verified": not CF_ENFORCE_STRICT, "mode": "OFFLINE_FALLBACK"}

