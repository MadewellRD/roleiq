import ai_provider


def test_parse_raw_json():
    assert ai_provider.parse_json_text('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    text = '```json\n{"a": 1, "b": [1, 2]}\n```'
    assert ai_provider.parse_json_text(text) == {"a": 1, "b": [1, 2]}


def test_parse_prose_wrapped_json():
    text = 'Sure, here is the result:\n{"a": 1}\nLet me know if you need more.'
    assert ai_provider.parse_json_text(text) == {"a": 1}


def test_parse_truncated_json_returns_none():
    text = '{"a": 1, "b": [1, 2'
    assert ai_provider.parse_json_text(text) is None


def test_parse_multiple_objects_returns_first_valid():
    # The first {...} span is malformed (trailing comma); the scanner should
    # skip it and return the next candidate that actually parses.
    text = 'Bad: {"a": 1,} Good: {"b": 2}'
    assert ai_provider.parse_json_text(text) == {"b": 2}


def test_balanced_objects_respects_strings_with_braces():
    text = '{"code": "if (x) { return 1; }"}'
    result = ai_provider.parse_json_text(text)
    assert result == {"code": "if (x) { return 1; }"}


def test_balanced_objects_respects_escaped_quotes():
    text = r'{"note": "she said \"hi\" near a { brace"}'
    result = ai_provider.parse_json_text(text)
    assert result == {"note": 'she said "hi" near a { brace'}


def test_strip_fences_handles_unterminated_fence():
    text = '```json\n{"a": 1, "b": '  # truncated, no closing fence
    assert ai_provider.parse_json_text(text) is None
