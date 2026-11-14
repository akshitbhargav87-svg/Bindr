"""Project setup must preserve existing security and fail before changing resources."""
from copy import deepcopy
import pytest
from scripts.configure_google_auth import identity_options


def config():
    return {"signIn": {"email": {"enabled": True, "passwordRequired": True}},
            "passwordPolicyConfig": {"passwordPolicyEnforcementState": "ENFORCE", "passwordPolicyVersions": [{"customStrengthOptions": {"minPasswordLength": 6, "maxPasswordLength": 128}}]},
            "authorizedDomains": ["existing.test"],
            "mfa": {"state": "MANDATORY", "enabledProviders": ["PHONE_SMS"], "providerConfigs": [{"state": "MANDATORY", "totpProviderConfig": {"adjacentIntervals": 0}}]}}


def test_setup_preserves_stricter_mfa_and_existing_domains_without_mutating_input():
    current = config(); before = deepcopy(current)
    result = identity_options(current, {"enabled": True}, ["bindr.run.app"])
    assert result["mfa"]["state"] == "MANDATORY"
    assert result["mfa"]["providerConfigs"][0] == {"state": "MANDATORY", "totpProviderConfig": {"adjacentIntervals": 0}}
    assert result["mfa"]["enabledProviders"] == ["PHONE_SMS"]
    assert result["authorizedDomains"] == ["bindr.run.app", "existing.test"]
    assert current == before


@pytest.mark.parametrize("gap", ["no_policy", "weak_policy", "different_minimum", "short_maximum", "long_maximum", "missing_maximum", "notify_policy", "anonymous", "duplicate", "google", "password"])
def test_setup_rejects_incomplete_identity_configuration(gap):
    current = config(); google = {"enabled": True}
    if gap == "no_policy": del current["passwordPolicyConfig"]
    strength = current.get("passwordPolicyConfig", {}).get("passwordPolicyVersions", [{}])[0].get("customStrengthOptions", {})
    if gap == "weak_policy": strength["minPasswordLength"] = 5
    if gap == "different_minimum": strength["minPasswordLength"] = 12
    if gap == "short_maximum": strength["maxPasswordLength"] = 64
    if gap == "long_maximum": strength["maxPasswordLength"] = 256
    if gap == "missing_maximum": del strength["maxPasswordLength"]
    if gap == "notify_policy": current["passwordPolicyConfig"]["passwordPolicyEnforcementState"] = "OFF"
    if gap == "anonymous": current["signIn"]["anonymous"] = {"enabled": True}
    if gap == "duplicate": current["signIn"]["allowDuplicateEmails"] = True
    if gap == "google": google["enabled"] = False
    if gap == "password": current["signIn"]["email"]["passwordRequired"] = False
    with pytest.raises(SystemExit):
        identity_options(current, google, [])
