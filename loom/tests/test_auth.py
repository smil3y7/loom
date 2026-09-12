# tests/test_auth.py
#
# Testi za lib/auth.py — pairing token za /api/ingest.

import os
import tempfile

from lib.auth import get_or_create_token, verify_token, regenerate_token


def test_creates_token_on_first_call():
    tmp = tempfile.mkdtemp()
    token = get_or_create_token(tmp)
    assert len(token) > 20
    assert os.path.isfile(os.path.join(tmp, "api_token"))


def test_returns_same_token_on_repeated_calls():
    """KLJUČNO — token se ne sme spremeniti med klici, sicer bi vsak
    restart backend procesa neveljavil obstoječi extension pairing."""
    tmp = tempfile.mkdtemp()
    first = get_or_create_token(tmp)
    second = get_or_create_token(tmp)
    third = get_or_create_token(tmp)
    assert first == second == third


def test_verify_token_accepts_correct_token():
    tmp = tempfile.mkdtemp()
    token = get_or_create_token(tmp)
    assert verify_token(token, tmp) is True


def test_verify_token_rejects_wrong_token():
    tmp = tempfile.mkdtemp()
    get_or_create_token(tmp)
    assert verify_token("popolnoma-napačen-token", tmp) is False


def test_verify_token_rejects_empty_or_none():
    tmp = tempfile.mkdtemp()
    get_or_create_token(tmp)
    assert verify_token("", tmp) is False
    assert verify_token(None, tmp) is False


def test_regenerate_token_invalidates_old_one():
    tmp = tempfile.mkdtemp()
    old = get_or_create_token(tmp)
    new = regenerate_token(tmp)
    assert new != old
    assert verify_token(old, tmp) is False
    assert verify_token(new, tmp) is True
    # In naslednji get_or_create_token mora vrniti NOVEGA, ne starega
    assert get_or_create_token(tmp) == new
