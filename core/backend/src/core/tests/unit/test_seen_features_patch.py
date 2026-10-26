"""Validation of the user-writable ``SeenFeaturesPatch`` body (key grammar, bounds, depth).

Pure pydantic: no DB and no ``app`` package.
"""

import pytest
from pydantic import ValidationError

from core.schemas.users import SeenFeaturesPatch


class TestSeenFeaturesPatchValidation:
    def test_accepts_valid(self):
        patch = SeenFeaturesPatch.model_validate({"reveal.profile_tab": True, "whatsnew.dashboard": {"v": 3}})
        assert patch.root["reveal.profile_tab"] is True
        assert patch.root["whatsnew.dashboard"] == {"v": 3}

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            SeenFeaturesPatch.model_validate({})

    @pytest.mark.parametrize(
        "bad_key",
        ["Reveal.ProfileTab", "reveal cat", "1reveal", "reveal..x", ".reveal", "reveal-name"],
    )
    def test_rejects_bad_keys(self, bad_key: str):
        with pytest.raises(ValidationError):
            SeenFeaturesPatch.model_validate({bad_key: True})

    def test_rejects_too_many_keys(self):
        with pytest.raises(ValidationError):
            SeenFeaturesPatch.model_validate({f"reveal.k{i}": True for i in range(21)})

    def test_rejects_nested_record(self):
        # Values are at most one level deep: a record may hold scalars only.
        with pytest.raises(ValidationError):
            SeenFeaturesPatch.model_validate({"nudge.x": {"a": {"b": 1}}})
