"""
This module provides a function to generate short codes for URLs in a deterministic
yet collision-safe manner. The generated short code can be used for URL shortening
services.

The approach combines:
1. A SHA-256 hash of the original URL (deterministic part)
2. Current timestamp in milliseconds (reduces collisions for concurrent requests)
3. A small random integer (further collision safety)
4. Base62 encoding to generate a short, URL-friendly string

This ensures:
- Same URL usually produces the same short code (deterministic-ish)
- High uniqueness across multiple requests
- Short codes suitable for URLs (alphanumeric, URL-safe)
"""

import hashlib
import time
import random
import string

BASE62 = string.ascii_letters + string.digits


def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62[0]

    result = []
    base = len(BASE62)
    while num:
        num, rem = divmod(num, base)
        result.append(BASE62[rem])
    return "".join(reversed(result))


def generate_short_code(url: str, length: int = 6, salt: str = "") -> str:
    hasher = hashlib.sha256()
    hasher.update(url.encode("utf-8"))
    hasher.update(salt.encode("utf-8"))
    hash_bytes = hasher.digest()[:5]  # take first 5 bytes → 40-bit deterministic part

    # Current timestamp in milliseconds (20-bit)
    ts_ms = int(time.time() * 1000) & 0xFFFFF

    # Small random part (10-bit)
    rand_part = random.randint(0, 2**10 - 1)

    # Combine hash, timestamp, and random part into a single integer
    combined = int.from_bytes(hash_bytes, "big")
    combined = (combined << 30) | (ts_ms << 10) | rand_part  # shift and combine bits

    # Encode combined integer to Base62 and truncate to desired length
    code = base62_encode(combined)
    return code[:length]
