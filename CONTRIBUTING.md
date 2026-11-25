# Contributing

Thanks for looking. This is a small tool, so the rules are short.

## Before you open a PR

- Open an issue for anything that changes behaviour (a new flag, a new output format, an exit code).
  Bug fixes with a test do not need one.
- Run the suite locally:

  ```bash
  python -m unittest discover -s tests -v
  ```

  CI runs the same command on Python 3.9, 3.11 and 3.13; a PR that fails any of them is not merged.

## What a good change looks like

- **Keep the exit-code contract.** `0` — everything open, `2` — bad arguments, `3` — the page could
  not be fetched or parsed, `4` — at least one vacancy is closed or unknown. Scripts depend on it.
- **No new dependencies.** Standard library only. That is the whole point of the tool.
- **No network in tests.** Add an HTML fixture under `tests/fixtures/` and drive the parser with it,
  the way the existing tests do.
- **No personal data in fixtures.** Names, phone numbers, e-mail addresses and document numbers in
  test data must be obviously fake (`example.com`, `+7 900 000-00-00`). A maintainer will ask you to
  rewrite the commit if real data ends up in a patch.
- **One concern per PR.** A fix and a refactor in one diff is hard to review.
- Keep the README honest: if a limit exists, it is written in the «Scope» section rather than hidden.

## Commits

Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, `test:`, `chore:`), English, imperative mood.
Squash-merge is used, so the PR title becomes the commit message.

## Adding a vacancy to the demo snapshot

The list in `tools/build_demo_data.py` (`DEFAULT_IDS`) is refreshed weekly by
`.github/workflows/snapshot.yml`. Add ids there if a specific case is worth showing permanently.
