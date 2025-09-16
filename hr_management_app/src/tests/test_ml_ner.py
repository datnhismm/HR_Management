try:
    from hr_management_app.src.ml.ner import extract_entities
except Exception:
    from ml.ner import extract_entities  # type: ignore


def test_ner_fallback_extracts_email_and_name():
    text = "Name: Bob Builder\nEmail: bob.builder@example.com\nDOB: 1980-01-01"
    out = extract_entities(text)
    assert out.get("email") == "bob.builder@example.com"
    assert "name" in out and out["name"].lower().startswith("bob")
