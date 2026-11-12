"""Admin-only audio decoding; routing performs authentication before calling this."""
import base64
import binascii
import secrets
from pathlib import Path
from .config import FRONTEND_DIR

MEDIA_DIR = FRONTEND_DIR / 'media' / 'uploads'
MAX_AUDIO_BYTES = 8 * 1024 * 1024


def upload_audio(payload):
    filename = payload.get('filename', '')
    encoded = payload.get('data_base64', '')
    if not isinstance(filename, str) or not isinstance(encoded, str):
        raise ValueError('Nama dan isi berkas audio tidak valid.')
    extension = Path(filename).suffix.lower()
    if extension not in {'.wav', '.mp3', '.ogg', '.m4a'}:
        raise ValueError('Gunakan audio WAV, MP3, OGG, atau M4A.')
    if len(encoded) > ((MAX_AUDIO_BYTES + 2) // 3) * 4:
        raise ValueError('Ukuran audio maksimal 8 MB.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('Isi berkas audio tidak dapat dibaca.') from error
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise ValueError('Ukuran audio harus di antara 1 byte dan 8 MB.')
    signatures = {
        '.wav': data[:4] == b'RIFF' and data[8:12] == b'WAVE',
        '.mp3': data[:3] == b'ID3' or (len(data) >= 2 and data[0] == 255 and data[1] & 224 == 224),
        '.ogg': data[:4] == b'OggS',
        '.m4a': data[4:8] == b'ftyp',
    }
    if not signatures[extension]:
        raise ValueError('Isi berkas tidak sesuai format audio yang dipilih.')
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = secrets.token_hex(16) + extension
    (MEDIA_DIR / safe_name).write_bytes(data)
    return {'status': 'ok', 'audio_url': '/media/uploads/' + safe_name, 'size_bytes': len(data)}
