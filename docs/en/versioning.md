# Versioning

**Revision r2.0.1 · Build date 2026-08-22**

## The scheme

`MAJOR.MINOR.PATCH`, with one project-specific rule:

| Part | Bumped when |
| --- | --- |
| **MAJOR** | **any feature extension** — a new token, a new preset, a new command, a new placement mode, a new front end. This is a project rule: every feature is a large change. |
| **MINOR** | behaviour-preserving improvements: refactoring, documentation, performance, new tests. |
| **PATCH** | bug fixes only. |

So adding a single new token takes r1.0.0 to r2.0.0. That is intentional: the
revision then tells you unambiguously whether a given capability exists.

## Where the revision lives

`src/lrfoldercraft/version.py` is the single source of truth:

```python
__version__   = "2.0.1"
__build_date__ = "2026-08-22"
__codename__   = "Wegweiser"
REVISION       = "r2.0.1 (2026-08-22)"
```

Nothing else hard-codes a version. Everything derives from this file:

- `lrfc --version` and every CLI report header
- the TUI header (`SUB_TITLE`)
- the first lines of every log file
- the `tool_version` field in the journal
- the `revision` field in exported plan JSON

## Where it is displayed

The requirement is that the tool **always** shows its revision and build date.
It does, in five places:

```console
$ lrfc --version
LR-FolderCraft r2.0.1 (2026-08-22) - Daybreak
```

```
LR-FolderCraft r2.0.1 (2026-08-22) - Daybreak      <- every report header
```

```
LR-FolderCraft — r2.0.1 (2026-08-22) - build 2026-08-22    <- TUI header
```

```
2026-08-22 16:26:31 | INFO | Revision r2.0.1 (2026-08-22) | version 1.0.0 | build date 2026-08-22
```

```json
{"event": "run-start", "tool_version": "1.0.0", ...}
```

## Releasing

1. Update `__version__`, `__build_date__` and, for a MAJOR bump, `__codename__`
   in `src/lrfoldercraft/version.py`.
2. Update `version` in `pyproject.toml` to match.
3. Add a `CHANGELOG.md` section.
4. Update the badges and the `**Revision …**` line at the top of every document
   in `docs/en/` and `docs/de/`.
5. If the release was verified against a new Lightroom catalog schema, add it to
   `VERIFIED_CATALOG_VERSIONS`.
6. Run the tests: `pytest`.
7. Commit as `release: rX.Y.Z — <summary>` and tag:

```bash
git tag -a v2.0.1 -m "LR-FolderCraft r1.0.0"
git push origin main --tags
```

There is a consistency check for step 1–2 in the test suite: `pyproject.toml`
and `version.py` must not drift apart.

## Catalog schema compatibility

Two constants in `version.py` govern this:

```python
VERIFIED_CATALOG_VERSIONS      = ("18.0.0",)   # tested against a real catalog
SUPPORTED_CATALOG_VERSION_RANGE = (11, 19)     # accepted without an override
```

- A **verified** version opens silently.
- A version inside the range but not verified opens with a warning.
- Anything outside the range is refused unless `--allow-unsupported-catalog` is
  given.

Adobe changes the schema between Lightroom Classic major releases. The tables
this tool uses (`AgLibraryRootFolder`, `AgLibraryFolder`, `AgLibraryFile`,
`Adobe_images`) have been stable for many years, but a new release should be
verified before it is added to `VERIFIED_CATALOG_VERSIONS`.

| Catalog schema | Lightroom Classic | Status |
| --- | --- | --- |
| 18.0.0 | 14.x | verified against a real 9,452-file catalog |
| 11.x–17.x | 7.x–13.x | expected to work, opens with a warning |
| 19.x | 15.x | inside the range, not yet verified |
| < 11 | ≤ 6 / Lightroom 6 | refused without an override |
