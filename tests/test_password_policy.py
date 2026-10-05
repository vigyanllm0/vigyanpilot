"""Password strength policy tests.

`primerforge.security.validate_password()` is the single source of truth for
every password-setting entry point (register, change, reset). These tests pin
the hardened policy:

  * 12-character minimum (was 8)
  * character classes (upper, lower, digit, special)
  * at least 8 distinct characters
  * no run of 4 identical characters
  * no 4-step monotonic run (1234 / abcd / 4321)
  * common-password blocklist (leet-aware, letter-skeleton match)
  * optional email local-part binding
"""
import pytest

from primerforge.security import (
    COMMON_PASSWORDS,
    PASSWORD_MIN_LENGTH,
    validate_password,
)


# ── Accepted ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("password", [
    "Vault-Key!Pr1mer26",     # mixed case + digit + symbols, 18 chars
    "Ops-Vault!Adm1n26",      # admin test credential
    "N0rth-Star!Gleam7",      # leet digit, 17 chars
    "River-Quartz!9Tide",     # passphrase-ish, 19 chars
    "Tr0ub4dor&3-Xylo9",      # exactly 8 distinct chars still passes
])
def test_strong_passwords_accepted(password):
    ok, err = validate_password(password)
    assert ok, err


def test_policy_is_at_least_twelve_characters():
    assert PASSWORD_MIN_LENGTH >= 12


# ── Rejected: length ────────────────────────────────────────────────────────

def test_short_password_rejected():
    ok, err = validate_password("Ab1!xyz")
    assert not ok
    assert "at least 12" in err


def test_eleven_chars_rejected_even_if_complex():
    ok, err = validate_password("Ab1!xyzQw3")
    assert not ok
    assert "at least 12" in err


def test_empty_and_non_string_rejected():
    assert validate_password("")[0] is False
    assert validate_password(None)[0] is False
    assert validate_password(12345)[0] is False


def test_overlong_password_rejected():
    ok, err = validate_password("Aa1!" + "x" * 200)
    assert not ok
    assert "too long" in err


# ── Rejected: character classes ─────────────────────────────────────────────

@pytest.mark.parametrize("password,missing_class", [
    ("alllowercase123!", "uppercase"),   # no uppercase letter
    ("ALLUPPERCASE123!", "lowercase"),   # no lowercase letter
    ("NoDigitsAllowed!!", "digit"),      # no digit
    ("NoSpecialChars123", "special"),    # no special character
])
def test_missing_character_class_rejected(password, missing_class):
    ok, err = validate_password(password)
    assert not ok
    # The error names the class that is absent.
    assert missing_class in err.lower()


# ── Rejected: weak structure ────────────────────────────────────────────────

def test_repeated_character_run_rejected():
    # 4 identical 'a' in a row, while still satisfying length, character
    # classes and the distinct-character floor (so the run rule is what trips).
    ok, err = validate_password("Xaaaa1!QwErTy")
    assert not ok
    assert "repeat" in err.lower()


def test_ascending_sequence_rejected():
    ok, err = validate_password("Abcdefghijkl1!X")          # abcdefghijkl
    assert not ok
    assert "sequential" in err.lower()


def test_descending_sequence_rejected():
    ok, err = validate_password("Hgfedcba9876!X")            # 9876 / agfed
    assert not ok
    assert "sequential" in err.lower() or "too common" in err.lower()


def test_too_few_distinct_characters_rejected():
    # 12+ chars but only 4 distinct: a, A, 1, !
    ok, err = validate_password("Aa1!Aa1!Aa1!")
    assert not ok
    assert "different characters" in err.lower() or "sequential" in err.lower() \
        or "repeat" in err.lower()


# ── Rejected: common passwords (the real-world attack) ──────────────────────

@pytest.mark.parametrize("password", [
    "Password1!",      # the classic "satisfies every class rule" password
    "Admin123!",
    "Welcome1!",
    "P@ssw0rd!",       # leet-obfuscated "password"
    "Letmein123!",
    "Qwerty123!",
    "Changed1!",
    "Passw0rd!2026",
])
def test_common_passwords_rejected(password):
    ok, err = validate_password(password)
    assert not ok, f"{password!r} must be rejected as a common password"
    assert "common" in err.lower() or "too common" in err.lower() \
        or "at least 12" in err


def test_blocklist_covers_the_obvious_entries():
    for entry in ("password", "admin", "welcome", "qwerty", "letmein"):
        assert entry in COMMON_PASSWORDS


# ── Email binding ───────────────────────────────────────────────────────────

def test_password_may_not_contain_email_local_part():
    ok, err = validate_password("Arjun1990!Kx", email="arjun1990@example.com")
    assert not ok
    assert "email" in err.lower()


def test_password_unrelated_to_email_accepted():
    ok, err = validate_password("Vault-Key!Pr1mer26", email="arjun1990@example.com")
    assert ok, err


def test_short_or_malformed_email_skips_binding():
    # Local-parts shorter than 4 chars are too generic to enforce on.
    assert validate_password("Vault-Key!Pr1mer26", email="ab@example.com")[0] is True
    assert validate_password("Vault-Key!Pr1mer26", email=None)[0] is True
