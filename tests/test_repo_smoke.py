from pathlib import Path


def test_readme_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'README.md').exists() or (root / 'README.MD').exists()
