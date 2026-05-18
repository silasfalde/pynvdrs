# Contributing

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[gpt,text,iaa]"
```

## Checks

```bash
pytest -q
ruff check pynvdrs tests
python -m build
python -m twine check dist/*
```

## Release process

1. Update `CHANGELOG.md`.
2. Bump the version in `pyproject.toml`.
3. Merge to `main`.
4. Tag the release with `vX.Y.Z`.
5. Let GitHub Actions build and publish the tag.