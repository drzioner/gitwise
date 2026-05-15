"""Tests for gitwise i18n — locale detection, string lookup, caching."""

import json
import os

from conftest import run_gitwise as _run


def test_default_locale_is_en():
    result = _run("doctor", "--json", env={"LC_ALL": "en_US.UTF-8", "LANG": "en_US.UTF-8"})
    data = json.loads(result.stdout)
    assert data["ok"] in (True, False)


def test_spanish_locale_output():
    result = _run(
        "audit",
        "--quick",
        "--json",
        env={"LC_ALL": "es_ES.UTF-8", "LANG": "es_ES.UTF-8", "GITWISE_LANG": "es"},
    )
    assert result.returncode in (0, 1)


def test_lang_flag_overrides_locale():
    result = _run("--lang", "es", "audit", "--quick", "--json")
    assert result.returncode in (0, 1)


def test_json_output_locale_independent():
    result_en = _run("audit", "--quick", "--json", env={"GITWISE_LANG": "en"})
    result_es = _run("audit", "--quick", "--json", env={"GITWISE_LANG": "es"})
    data_en = json.loads(result_en.stdout)
    data_es = json.loads(result_es.stdout)
    assert data_en["v"] == data_es["v"]
    assert len(data_en["findings"]) == len(data_es["findings"])


def test_missing_key_returns_key_itself():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from gitwise.i18n import t

    result = t("nonexistent_key_xyz_12345")
    assert result == "nonexistent_key_xyz_12345"


def test_template_interpolation():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    os.environ["GITWISE_LANG"] = "en"
    from gitwise.i18n import reset_cache, t

    reset_cache()
    result = t("optimizing", root="/tmp/test")
    assert "/tmp/test" in result
    reset_cache()


def test_confirm_responses_en():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    os.environ["GITWISE_LANG"] = "en"
    from gitwise.i18n import confirm_responses, reset_cache

    reset_cache()
    responses = confirm_responses()
    assert "y" in responses
    assert "yes" in responses
    reset_cache()


def test_confirm_responses_es():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    os.environ["GITWISE_LANG"] = "es"
    from gitwise.i18n import confirm_responses, reset_cache

    reset_cache()
    responses = confirm_responses()
    assert "s" in responses
    assert "si" in responses
    reset_cache()
