from __future__ import annotations

import operator

import pytest

from metrka_core.quality.models import QualityCheckInput, QualityGate


def test_quality_check_input_copies_and_freezes_both_namespaces() -> None:
    context = {"is_zip": False}
    params = {"is_zip": True}
    check_input = QualityCheckInput(
        context=context,
        params=params,
        check_id="zip-check",
        quality_gate=QualityGate.PRE_BRONZE,
        applies_to={},
    )

    context["is_zip"] = True
    params["is_zip"] = False

    assert check_input.context["is_zip"] is False
    assert check_input.params["is_zip"] is True

    with pytest.raises(TypeError):
        operator.setitem(check_input.context, "is_zip", True)

    with pytest.raises(TypeError):
        operator.setitem(check_input.params, "is_zip", False)
