from __future__ import annotations

import re


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:(?:\+?1[-.\s]*)?)?(?:\(?\d{3}\)?[-.\s]*)\d{3}[-.\s]*\d{4}\b"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
URL_RE = re.compile(r"\bhttps?://[^\s)]+", re.IGNORECASE)

# Common key-ish patterns (intentionally conservative).
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
GOOGLE_KEY_RE = re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")

# CC candidate: digits with optional separators; validate with Luhn.
CC_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

# Banking (conservative; typically require nearby keywords in detect.py).
ROUTING_9_RE = re.compile(r"\b\d{9}\b")
ACCOUNT_NUM_RE = re.compile(r"\b\d{8,17}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
SWIFT_BIC_RE = re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b")


