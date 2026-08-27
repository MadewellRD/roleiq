import app


def test_deterministic():
    resume = "Jane Doe\nSenior Engineer\n10 years experience"
    assert app.candidate_id(resume) == app.candidate_id(resume)


def test_changes_with_content():
    a = app.candidate_id("Resume text A")
    b = app.candidate_id("Resume text B")
    assert a != b


def test_normalizes_whitespace():
    # candidate_id runs clean_text() first, so re-uploading the same resume
    # with different line endings / trailing whitespace still dedups to the
    # same row -- this is the documented, intentional dedup-by-content design.
    a = app.candidate_id("Line one\r\nLine two\r\n\r\n\r\nLine three   ")
    b = app.candidate_id("Line one\nLine two\n\nLine three")
    assert a == b


def test_length_and_hex_format():
    cid = app.candidate_id("some resume text")
    assert len(cid) == 16
    int(cid, 16)  # raises ValueError if not valid hex
