# hh-vacancy-check

[![tests](https://github.com/basovdanil/hh-vacancy-check/actions/workflows/tests.yml/badge.svg)](https://github.com/basovdanil/hh-vacancy-check/actions/workflows/tests.yml)

**English** · [Русский](README.md)

Checks whether hh.ru vacancies are still open, without logging in and without an API token.

## Why it exists

hh keeps an archived vacancy page online, and the page template always contains the phrase
«Вакансия в архиве» — so a plain text search reports every posting as archived. The reliable signal
is the schema.org `JobPosting` block: its `validThrough` field is the employer's deadline, and hh
strips the block from postings it has closed.

```bash
python vacancy_check.py 139441388 139528682 139578310
```

```
OPEN      139441388  2026-12-12  Аналитик данных
CLOSED    139528682  2026-11-23  Специалист по прогнозированию в Гипер Лента
                     validThrough has passed
OPEN      139578310  2026-12-17  Аналитик данных (качество данных)
```

Exit code `4` — at least one vacancy is closed, so it can gate a script that collects postings.

## Usage

```
python vacancy_check.py <id|url> [<id|url> ...] [--json]
```

- accepts bare ids and full URLs (`https://hh.ru/vacancy/139441388?query=x`);
- `--json` prints one object per vacancy to stdout, no colour, no progress;
- standard library only, Python 3.8+.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | every vacancy is open |
| `2` | bad arguments |
| `3` | the page could not be fetched or parsed |
| `4` | at least one vacancy is closed or unknown |

## How the check is done

1. Fetch the vacancy page with a normal browser User-Agent.
2. Find the `application/ld+json` block with `"@type": "JobPosting"`.
3. Compare `validThrough` with the current time.
4. No block at all means the posting is closed or removed; a block without `validThrough` is
   reported as `unknown`, not as open.

No cookies, no login, no private endpoints — one public page per vacancy.

## Tests

```
python -m unittest discover -s tests
```

16 tests on saved HTML fixtures: open/expired/missing-deadline/archived pages, broken JSON-LD,
non-JobPosting blocks, id extraction from URLs, and every exit code. The test suite never touches
the network.

## Scope

hh.ru only, and only the public page. Rate: one request per vacancy with no parallelism; the site
may throttle a burst of requests, so the tool is meant for dozens of links, not thousands.

It reports the employer's deadline, not the employer's intent: a vacancy can be `OPEN` and still be
filled.
