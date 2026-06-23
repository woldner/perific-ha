# Release

This repo uses Python Semantic Release for versioning, changelog updates, tags,
and GitHub Releases. Do not add `package.json`, npm release tooling, or Nx
unless the repo gains a real JavaScript build surface.

Release automation updates both version fields:

- `pyproject.toml:project.version`
- `custom_components/perific/manifest.json:version`

The first GitHub Release must be created manually from the current known-good
state:

```sh
gh release create v0.1.0 --target main --title v0.1.0 --notes "Initial dogfooding release."
```

After the initial release exists, pushes to `main` run validation and create a
new GitHub Release when Conventional Commits require a SemVer bump.

Before changing release automation, run:

```sh
uv run pytest tests/test_release_metadata.py
uvx --from python-semantic-release==10.5.3 semantic-release --noop version --no-push --no-vcs-release
```
