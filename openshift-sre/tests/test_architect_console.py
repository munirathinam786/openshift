from pathlib import Path


def test_architect_console_preloads_red_hat_libraries_via_embed_configuration():
    source = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "assets"
        / "javascripts"
        / "architect-console.js"
    ).read_text(encoding="utf-8")

    assert "configure=1" in source
    assert "payload.event === 'configure'" in source
    assert "defaultLibraries" in source
    assert "defaultCustomLibraries" in source
    assert "official Red Hat libraries preloaded" in source