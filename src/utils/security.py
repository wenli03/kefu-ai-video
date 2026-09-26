"""
安全模块

提供：
1. 数据加密（AES-GCM 加密敏感字段）
2. 输入验证与清洗
3. 敏感信息检测与脱敏
4. DDoS 防护（令牌桶限流）
"""

import hashlib
import hmac
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .logging import SessionLogger

_log = SessionLogger("security")


# ─── 数据加密 ────────────────────────────────────────────────────────────────

class DataEncryptor:
    """
    数据加密器

    使用 AES-GCM 模式加密敏感数据。
    生产环境应使用 cryptography 库，这里提供接口定义和基于标准库的简化实现。
    """

    def __init__(self, master_key: Optional[bytes] = None):
        self._master_key = master_key or os.urandom(32)
        self._field_keys: dict[str, bytes] = {}

    def _derive_field_key(self, field_name: str) -> bytes:
        if field_name not in self._field_keys:
            self._field_keys[field_name] = hashlib.sha256(
                self._master_key + field_name.encode()
            ).digest()
        return self._field_keys[field_name]

    def encrypt_field(self, value: str, field_name: str) -> str:
        """加密单个字段，返回 base64 编码的密文"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = self._derive_field_key(field_name)
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, value.encode(), None)
            import base64
            return base64.b64encode(nonce + ciphertext).decode()
        except ImportError:
            _log.warning("encryption_fallback", reason="cryptography not installed")
            return self._simple_encrypt(value, field_name)

    def decrypt_field(self, encrypted: str, field_name: str) -> str:
        """解密字段"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import base64
            key = self._derive_field_key(field_name)
            aesgcm = AESGCM(key)
            raw = base64.b64decode(encrypted)
            nonce, ciphertext = raw[:12], raw[12:]
            return aesgcm.decrypt(nonce, ciphertext, None).decode()
        except ImportError:
            return self._simple_decrypt(encrypted, field_name)

    def _simple_encrypt(self, value: str, field_name: str) -> str:
        """简化加密（XOR + base64），仅用于开发环境"""
        key = self._derive_field_key(field_name)
        value_bytes = value.encode()
        encrypted = bytes(
            v ^ key[i % len(key)] for i, v in enumerate(value_bytes)
        )
        import base64
        return "SIMPLE:" + base64.b64encode(encrypted).decode()

    def _simple_decrypt(self, encrypted: str, field_name: str) -> str:
        if not encrypted.startswith("SIMPLE:"):
            raise ValueError("Invalid encrypted data")
        import base64
        key = self._derive_field_key(field_name)
        raw = base64.b64decode(encrypted[7:])
        decrypted = bytes(
            v ^ key[i % len(key)] for i, v in enumerate(raw)
        )
        return decrypted.decode()

    def hash_value(self, value: str, salt: str = "") -> str:
        """单向哈希（用于密码等不可逆场景）"""
        return hashlib.sha256((salt + value).encode()).hexdigest()

    def sign_value(self, value: str) -> str:
        """HMAC 签名（用于防篡改）"""
        return hmac.new(self._master_key, value.encode(), hashlib.sha256).hexdigest()


# ─── 敏感信息检测 ──────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = {
    "id_card": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "bank_card": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "address": re.compile(r"(?:省|市|区|县|镇|乡|村|路|号|街|栋|单元|室){2,}"),
}


def detect_sensitive_info(text: str) -> dict[str, list[str]]:
    """检测文本中的敏感信息"""
    found = {}
    for name, pattern in SENSITIVE_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[name] = matches
    return found


def mask_sensitive_info(text: str) -> str:
    """脱敏处理"""
    result = text
    result = re.sub(r"(?<!\d)(\d{3})\d{4}(\d{4})(?!\d)", r"\1****\2", result)
    result = re.sub(r"(?<!\d)(\d{6})\d{8}(\d{4})(?!\d)", r"\1********\2", result)
    result = re.sub(
        r"(\w{2})[\w.-]+@([\w.-]+\.\w+)", r"\1***@\2", result
    )
    result = re.sub(r"(?<!\d)(\d{4})\d{8,11}(\d{4})(?!\d)", r"\1****\2", result)
    return result


def validate_input(text: str, max_length: int = 1000) -> tuple[bool, str]:
    """
    输入验证

    检查：
    1. 长度限制
    2. SQL 注入特征
    3. XSS 特征
    4. Prompt 注入特征
    """
    if not text or not text.strip():
        return False, "输入不能为空"

    if len(text) > max_length:
        return False, f"输入长度超过限制 ({max_length})"

    sql_patterns = [
        r"(?:union\s+select|drop\s+table|insert\s+into|delete\s+from)",
        r"(?:'\s*or\s+'1'\s*=\s*'1|'\s*;\s*--)",
        r"(?:exec\s*\(|execute\s*\()",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "检测到非法输入 (SQL 注入特征)"

    xss_patterns = [
        r"<script[^>]*>",
        r"javascript\s*:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]
    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "检测到非法输入 (XSS 特征)"

    prompt_injection_patterns = [
        r"(?:ignore\s+(?:previous|above)\s+instructions)",
        r"(?:you\s+are\s+now\s+(?:a|an)\s+)",
        r"(?:system\s*:\s*)",
        r"(?:do\s+not\s+follow\s+(?:your|the)\s+)",
    ]
    for pattern in prompt_injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "检测到非法输入 (Prompt 注入特征)"

    return True, ""


def sanitize_text(text: str) -> str:
    """清洗文本，移除危险字符"""
    text = text.strip()
    text = re.sub(r"[<>]", "", text)
    text = re.sub(r"javascript\s*:", "", text, flags=re.IGNORECASE)
    return text


# ─── DDoS 防护：令牌桶限流 ──────────────────────────────────────────────────

@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: float = 0.0


class TokenBucketRateLimiter:
    """
    令牌桶限流器

    每个用户/IP 独立限流
    """

    def __init__(
        self,
        rate: float = 10.0,
        capacity: int = 20,
        per_seconds: float = 60.0,
    ):
        self.rate = rate
        self.capacity = capacity
        self.per_seconds = per_seconds
        self._buckets: dict[str, dict] = {}

    def check(self, key: str) -> RateLimitResult:
        now = time.time()

        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.capacity,
                "last_refill": now,
            }

        bucket = self._buckets[key]
        elapsed = now - bucket["last_refill"]
        refill = elapsed * (self.rate / self.per_seconds)
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + refill)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket["tokens"]),
            )

        retry_after = (1 - bucket["tokens"]) * (self.per_seconds / self.rate)
        return RateLimitResult(
            allowed=False,
            remaining=0,
            retry_after=retry_after,
        )

    def cleanup(self, max_age: float = 3600.0):
        """清理过期桶"""
        now = time.time()
        expired = [
            k for k, v in self._buckets.items()
            if now - v["last_refill"] > max_age
        ]
        for k in expired:
            del self._buckets[k]


class IPBlacklist:
    """IP 黑名单管理"""

    def __init__(self, auto_block_threshold: int = 100, window: float = 60.0):
        self._blacklist: dict[str, float] = {}
        self._violation_counts: dict[str, int] = defaultdict(int)
        self._auto_block_threshold = auto_block_threshold
        self._window = window

    def is_blocked(self, ip: str) -> bool:
        if ip in self._blacklist:
            if time.time() < self._blacklist[ip]:
                return True
            del self._blacklist[ip]
        return False

    def record_violation(self, ip: str):
        self._violation_counts[ip] += 1
        if self._violation_counts[ip] >= self._auto_block_threshold:
            self.block(ip, duration=3600.0)
            _log.warning("ip_auto_blocked", ip=ip)

    def block(self, ip: str, duration: float = 3600.0):
        self._blacklist[ip] = time.time() + duration
        _log.info("ip_blocked", ip=ip, duration=duration)

    def unblock(self, ip: str):
        self._blacklist.pop(ip, None)
        self._violation_counts.pop(ip, None)


# ─── 全局实例 ────────────────────────────────────────────────────────────────

encryptor = DataEncryptor()
rate_limiter = TokenBucketRateLimiter(rate=10, capacity=20, per_seconds=60)
ip_blacklist = IPBlacklist()
