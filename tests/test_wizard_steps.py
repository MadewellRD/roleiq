import app


def test_build_steps_with_role_context_enabled():
    steps = app.build_steps(True)
    assert len(steps) == 6
    assert ("role_context", "Role Context") in steps


def test_build_steps_without_role_context():
    steps = app.build_steps(False)
    assert len(steps) == 5
    assert "role_context" not in [k for k, _ in steps]


def test_build_steps_preserves_relative_order_of_remaining_steps():
    with_ctx = [k for k, _ in app.build_steps(True) if k != "role_context"]
    without_ctx = [k for k, _ in app.build_steps(False)]
    assert with_ctx == without_ctx == [
        "readiness_map", "experience_graph", "sme_training", "interview", "sources_battle_card",
    ]


def _comp(interview_risk=None):
    d = {"name": f"comp-{interview_risk}"}
    if interview_risk is not None:
        d["interview_risk"] = interview_risk
    return d


def test_ordered_competencies_sorts_by_risk_high_first():
    analysis = {"competencies": [
        _comp("Low"),      # 0
        _comp("High"),     # 1
        _comp("Medium"),   # 2
        _comp("High"),     # 3
        _comp(""),         # 4
        _comp(None),       # 5 (missing key entirely, since interview_risk omitted)
    ]}
    ordered = app.ordered_competencies(analysis)
    indices = [idx for idx, _ in ordered]
    # Both High entries (1, 3) first and in original relative order (stable
    # sort), then Medium (2), then Low (0), then the two lowest-priority
    # (empty/missing) entries (4, 5) in original relative order.
    assert indices == [1, 3, 2, 0, 4, 5]


def test_ordered_competencies_treats_unrecognized_value_as_lowest_priority():
    analysis = {"competencies": [_comp("High"), _comp("Critical")]}
    ordered = app.ordered_competencies(analysis)
    indices = [idx for idx, _ in ordered]
    assert indices == [0, 1]


def test_ordered_competencies_empty():
    assert app.ordered_competencies({"competencies": []}) == []
    assert app.ordered_competencies({}) == []


def test_recommended_step_empty_visited_returns_first():
    assert app.recommended_step(["a", "b", "c"], set()) == "a"


def test_recommended_step_returns_first_unvisited():
    assert app.recommended_step(["a", "b", "c", "d"], {"a", "b"}) == "c"


def test_recommended_step_all_visited_returns_none():
    # Nothing left to recommend once every step has been seen -- must not
    # collapse to "the last step," which would nudge back to it forever.
    assert app.recommended_step(["a", "b"], {"a", "b"}) is None


def test_recommended_step_empty_list_returns_none():
    assert app.recommended_step([], set()) is None


def test_competency_progress_empty():
    assert app.competency_progress([], {}) == (0, 0)


def test_competency_progress_partial():
    ordered = [(0, _comp("High")), (1, _comp("Medium")), (2, _comp("Low"))]
    trained = {0: {"what_it_means": "x"}}
    assert app.competency_progress(ordered, trained) == (1, 3)


def test_competency_progress_ignores_stale_index_not_in_ordered():
    ordered = [(0, _comp("High")), (1, _comp("Medium"))]
    trained = {0: {}, 5: {}}  # index 5 doesn't exist in `ordered`
    assert app.competency_progress(ordered, trained) == (1, 2)
