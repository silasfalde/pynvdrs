# pynvdrs — Maintainer Instructions

Purpose: actionable checklist and instructions for the agent/responsible developer to finish, publish, and maintain the `pynvdrs` package so downstream research repos (like `pr-ifip`) can depend on it.

Prerequisites
- GitHub repo created and pushed (name: `pynvdrs`).
- PyPI account or GitHub Packages access and a PyPI API token (if publishing to PyPI).
- Recommended Python versions to support: 3.9, 3.10, 3.11. Update CI matrix accordingly.

High-level roadmap
1. Finalize package API and extract implementations from `pr-ifip` into this repo.
2. Make heavy/optional dependencies extras and perform lazy imports.
3. Add unit tests, fixtures, and CI workflows (test + lint + release).
4. Document usage and migration notes for downstream repos.
5. Publish first release (v0.1.0) to PyPI (or GitHub Packages) and add integration instructions for downstream projects.

Detailed tasks

1) Code extraction and API design
- Copy full implementations from `pr-ifip/src/*` into `pynvdrs/pynvdrs/` replacing stubs: `paths.py`, `umgpt.py`, `nvdrs.py` -> `text.py`, `annotation.py`, `demographics.py`.
- Remove hardcoded project-specific state: replace constants like `CASES_CSV`, `PROJECT_ROOT` with function parameters or small helper getters.
- Design a minimal, stable public surface for each module. Example suggestions:
  - `paths.project_root(start_path=None) -> Path`
  - `paths.data_dir(env_var='DATA_DIR', default='data') -> Path`
  - `umgpt.GPTClient(client=None, model=None)` + `generate(prompt, **kwargs)`
  - `text.clean_text(text)` and `text.load_symspell(dictionary_path=None) -> SymSpell` and `text.correct_spelling(text, symspell)`
  - `annotation.find_disagreements(df, annotator_cols)` and `annotation.iaa_*` helpers
  - `demographics.bin_age(age)` and other pure transforms
- Prefer small, well-documented functions that accept inputs rather than reading global paths or env variables internally.

2) Dependency management
- Keep core dependencies minimal: `pandas`, `numpy` in `pyproject.toml` under `project.dependencies`.
- Move heavy or optional deps to extras:
  - `gpt` extra: `openai` (or `azure-openai` if applicable)
  - `text` extra: `symspellpy`
  - `iaa` extra: `krippendorff`, `scikit-learn`
- Use lazy imports within functions that require optional packages. Example:
  ```py
  def compute_krippendorff(...):
      try:
          import krippendorff
      except ImportError as e:
          raise RuntimeError("Install pynvdrs[iaa] to use IAA utilities") from e
      # function body
  ```

3) Tests
- Add unit tests covering:
  - `paths` helpers (resolve project root, data dir env override)
  - `text` cleaning and symspell integration (mock symspell if required)
  - `annotation` functions (small synthetic DataFrame tests)
  - `umgpt` wrapper: test that `GPTClient.generate` raises with no client and works with a minimal mock object
- Keep tests fast and avoid large datasets. Use small fixtures embedded in `tests/fixtures/`.
- Add linters: `ruff` or `flake8` and `black` for formatting; add to CI.

4) Continuous Integration
- Add GitHub Actions workflow(s):
  - `ci.yml` (runs on push/PR): setup Python matrix (3.9-3.11), install extras `pip install -e .[gpt,text,iaa]` only for relevant jobs or test matrix.
  - `release.yml`: on tag, build a wheel and publish to PyPI using `pypa/gh-action-pypi-publish` with `PYPI_API_TOKEN` secret.
- Add job steps for: install, run linters, run tests, build package.

5) Documentation and examples
- Update `README.md` with:
  - Short description
  - Quick install (PyPI or git install) and `pip install pynvdrs[ gpt , text ]` examples
  - Minimal usage examples for each module (copy small snippets from `pr-ifip` but parameterized)
- Add a `docs/` folder (optional) with a short `usage.md` and an `examples/` folder containing tiny, runnable scripts demonstrating common workflows (text cleaning, GPT call, computing disagreements).

6) Versioning, changelog, and release process
- Use semantic versioning. Start at `0.1.0` for the first stable public release.
- Keep an `HISTORY.md` or `CHANGELOG.md` and update it for each release.
- Tag releases on GitHub and use GitHub Actions to publish.

7) Backwards-compatibility and migration shims
- Provide compatibility shims for `pr-ifip` to reduce friction during migration. Example shim `src/paths.py` in `pr-ifip`:
  ```py
  try:
      from pynvdrs.paths import *
  except Exception:
      # fallback local implementation
      from ._paths_fallback import *
  ```
- Prefer not to delete original files in `pr-ifip` until `pynvdrs` is published and downstream CI green.

8) Publishing to PyPI (step-by-step)
- Create a PyPI account and generate an API token: https://pypi.org/manage/account/
- Add `PYPI_API_TOKEN` to GitHub repo secrets for `pynvdrs` (Settings → Secrets → Actions).
- Locally build and test before publishing:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip build twine
  python -m build
  python -m twine check dist/*
  # optional: test upload to TestPyPI
  python -m twine upload --repository testpypi dist/* -u __token__ -p $TESTPYPI_API_TOKEN
  # publish to PyPI
  python -m twine upload dist/* -u __token__ -p $PYPI_API_TOKEN
  ```
- Prefer automating publishing via GitHub Actions on tag push using `pypa/gh-action-pypi-publish`.

9) Post-publish: integrate with downstream repos
- In downstream repos (e.g., `pr-ifip`) update `requirements.txt` or `pyproject.toml`:
  - `pynvdrs>=0.1.0`
  - If using extras: `pynvdrs[gpt,text]>=0.1.0`
- Add short migration docs for maintainers: mapping of old imports to new imports and examples of how to call functions with the new signature.
- Replace local modules with shims and run downstream CI and smoke tests.

10) Maintenance and governance
- Add CODE_OF_CONDUCT.md and CONTRIBUTING.md to guide contributions.
- Add issue and PR templates for reporting bugs, requesting features, and publishing releases.
- Define a small set of maintainers and release gatekeepers; store contact info in `MAINTAINERS.md`.

Developer workflow (local)
- Clone `pynvdrs` and create a virtualenv. Use editable install during development:
  ```bash
  git clone git@github.com:<you>/pynvdrs.git
  cd pynvdrs
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install -e .[gpt,text,iaa]
  pytest -q
  ```
- To test integration with `pr-ifip` locally:
  ```bash
  # from parent directory
  pip install -e pynvdrs[ gpt , text ]
  cd pr-ifip
  # run a small script that imports the package
  python -c "import pynvdrs; print(pynvdrs.paths.project_root())"
  ```

Security and privacy
- Do not commit API keys or secrets to the repository. Use GitHub Secrets for publishing keys.
- Audit any external dependencies for licensing and security concerns before adding them to `project.dependencies`.

Checklist before first public release
- [ ] All selected modules copied and refactored to remove project-specific hardcoding
- [ ] API surface documented in `README.md` and `docs/`
- [ ] Unit tests added with >80% coverage for public functions (aim for focused tests)
- [ ] CI workflow passes (lint + tests) for supported Python versions
- [ ] `pyproject.toml` finalized with optional extras
- [ ] `CHANGELOG.md` prepared
- [ ] `LICENSE` file added
- [ ] GitHub repository settings configured (branch protection, secrets)
- [ ] PyPI API token stored in GitHub Secrets
- [ ] Release tag created and publishing automated

If you want, I can now:
- Extract the actual implementations from `pr-ifip/src/` into `pynvdrs/pynvdrs/` and make the parameterization changes (code edits). OR
- Generate the shim files for `pr-ifip` to delegate to `pynvdrs` immediately so you can test local integration.

End of instructions.
