import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from app.core.config import settings

# --- Password Hashing Setup with Resilient Fallbacks ---
try:
    import bcrypt

    def hash_password(password: str) -> str:
        # bcrypt handles maximum 72 bytes
        pwd_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            pwd_bytes = plain_password.encode("utf-8")[:72]
            return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False

except ImportError:
    try:
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        def hash_password(password: str) -> str:
            return pwd_context.hash(password[:72])

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            try:
                return pwd_context.verify(plain_password[:72], hashed_password)
            except Exception:
                return False

    except ImportError:
        import os

        # Cryptographically secure PBKDF2-HMAC-SHA256 fallback
        def hash_password(password: str) -> str:
            salt = os.urandom(16)
            derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
            salt_b64 = base64.b64encode(salt).decode("ascii")
            hash_b64 = base64.b64encode(derived).decode("ascii")
            return f"pbkdf2_sha256${salt_b64}${hash_b64}"

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            try:
                algo, salt_b64, hash_b64 = hashed_password.split("$")
                salt = base64.b64decode(salt_b64)
                derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
                return hmac.compare_digest(base64.b64encode(derived).decode("ascii"), hash_b64)
            except Exception:
                return False


# --- JWT Token Management with PyJWT / Jose / Stdlib Fallback ---

try:
    import jwt as pyjwt

    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return pyjwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            return pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except Exception:
            return None

except ImportError:
    try:
        from jose import JWTError, jwt as jose_jwt

        def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
            to_encode.update({"exp": expire})
            return jose_jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
            try:
                return jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            except JWTError:
                return None

    except ImportError:
        # High-precision Pure Python HS256 implementation (Zero dependencies)
        def _b64url_encode(raw_bytes: bytes) -> str:
            return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")

        def _b64url_decode(raw_str: str) -> bytes:
            padding = 4 - (len(raw_str) % 4)
            if padding != 4:
                raw_str += "=" * padding
            return base64.urlsafe_b64decode(raw_str.encode("ascii"))

        def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
            header = {"typ": "JWT", "alg": "HS256"}
            payload = data.copy()
            expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
            payload["exp"] = int(expire.timestamp())

            encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
            encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            signing_input = f"{encoded_header}.{encoded_payload}"

            signature = hmac.new(
                settings.SECRET_KEY.encode("utf-8"),
                signing_input.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            encoded_signature = _b64url_encode(signature)

            return f"{signing_input}.{encoded_signature}"

        def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
            try:
                parts = token.split(".")
                if len(parts) != 3:
                    return None
                header_b64, payload_b64, signature_b64 = parts
                signing_input = f"{header_b64}.{payload_b64}"

                expected_signature = hmac.new(
                    settings.SECRET_KEY.encode("utf-8"),
                    signing_input.encode("utf-8"),
                    hashlib.sha256,
                ).digest()

                if not hmac.compare_digest(_b64url_encode(expected_signature), signature_b64):
                    return None

                payload_bytes = _b64url_decode(payload_b64)
                payload = json.loads(payload_bytes.decode("utf-8"))

                # Expiration check
                exp = payload.get("exp")
                if exp and datetime.now(timezone.utc).timestamp() > exp:
                    return None

                return payload
            except Exception:
                return None
