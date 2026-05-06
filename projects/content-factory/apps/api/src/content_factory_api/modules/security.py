import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def expires_in(**kwargs: int) -> datetime:
    return utcnow() + timedelta(**kwargs)


def create_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_secret(secret: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${digest}"


def verify_secret(secret: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_digest = stored_hash.split("$", maxsplit=3)
        iterations = int(iterations_text)
    except ValueError:
        return False

    if algorithm != HASH_ALGORITHM:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)
