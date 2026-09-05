from deproc.core.interfaces.resolver import ResolutionResult, ResolutionStatus


def test_resolution_result_represents_ambiguous_candidates():
    result = ResolutionResult[str](
        status=ResolutionStatus.AMBIGUOUS,
        candidates=("first", "second"),
        reason="multiple matches",
    )

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.value is None
    assert result.candidates == ("first", "second")
