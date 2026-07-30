import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt
import pytest

from api.auth import require_role


class FakeHttpRequest:
    def __init__(self, headers: dict):
        self.headers = headers


def _fake_token(roles: list[str]) -> str:
    return jwt.encode({"roles": roles}, "test-secret", algorithm="HS256")


def test_require_role_rejects_missing_authorization_header():
    req = FakeHttpRequest({})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is False
    assert response.status_code == 401


def test_require_role_rejects_missing_role():
    token = _fake_token(["audit-viewer"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is False
    assert response.status_code == 403


def test_require_role_allows_matching_role():
    token = _fake_token(["compliance-admin"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is True
    assert response is None


def test_require_role_rejects_malformed_token():
    req = FakeHttpRequest({"Authorization": "Bearer not-a-real-jwt"})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is False
    assert response.status_code == 401


def test_require_role_with_role_set_allows_any_matching_role():
    token = _fake_token(["audit-viewer"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(
        req, {"audit-viewer", "compliance-admin"}, _decode_unverified=True
    )
    assert allowed is True
    assert response is None


def test_require_role_with_role_set_allows_other_matching_role():
    token = _fake_token(["compliance-admin"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(
        req, {"audit-viewer", "compliance-admin"}, _decode_unverified=True
    )
    assert allowed is True
    assert response is None


def test_require_role_with_role_set_rejects_when_no_role_matches():
    token = _fake_token(["some-other-role"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(
        req, {"audit-viewer", "compliance-admin"}, _decode_unverified=True
    )
    assert allowed is False
    assert response.status_code == 403


def test_require_role_allows_app_only_token_with_roles_but_no_scp():
    token = jwt.encode({"roles": ["compliance-admin"]}, "test-secret", algorithm="HS256")
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is True
    assert response is None


def test_require_role_rejects_token_with_neither_scp_nor_roles():
    token = jwt.encode({"sub": "someone"}, "test-secret", algorithm="HS256")
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    allowed, response = require_role(req, "compliance-admin", _decode_unverified=True)
    assert allowed is False
    assert response.status_code == 401


class _FakeSysWithoutPytest:
    modules: dict = {}


def test_require_role_test_mode_raises_outside_pytest(monkeypatch):
    import api.auth as auth_module

    token = _fake_token(["compliance-admin"])
    req = FakeHttpRequest({"Authorization": f"Bearer {token}"})
    monkeypatch.setattr(auth_module, "sys", _FakeSysWithoutPytest)
    with pytest.raises(RuntimeError):
        require_role(req, "compliance-admin", _decode_unverified=True)
