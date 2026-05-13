from pathlib import Path


def test_ml_layer_has_no_ga4_domain_keywords():
    keywords = [
        "sessions",
        "ecommerce",
        "eventName",
        "channel",
        "sourceMedium",
        "sessionSourceMedium",
    ]
    ml_files = Path("app/ml").rglob("*.py")
    source = "\n".join(path.read_text(encoding="utf-8") for path in ml_files)

    for keyword in keywords:
        assert keyword not in source
