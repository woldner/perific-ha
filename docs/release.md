# Release

This repo uses Python Semantic Release for versioning, changelog updates, tags,
and GitHub Releases. Do not add `package.json`, npm release tooling, or Nx
unless the repo gains a real JavaScript build surface.

Release automation updates both version fields:

- `pyproject.toml:project.version`
- `custom_components/perific/manifest.json:version`

An initial GitHub Release baseline exists. Do not recreate the baseline or
create manual release tags during normal development. If release history must
be repaired, identify the target commit first and verify the semantic release
no-op command before changing GitHub release state.

Pushes to `main` run validation and create a new GitHub Release when
Conventional Commits require a SemVer bump.

Before changing release automation, run:

```sh
uv run pytest tests/test_release_metadata.py
uvx --from python-semantic-release==10.5.3 semantic-release --noop version --no-push --no-vcs-release
```
