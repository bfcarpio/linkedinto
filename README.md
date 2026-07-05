# linkedinto

Convert a LinkedIn export ZIP to [JSON Resume](https://jsonresume.org/) and [RenderCV](https://rendercv.com/) YAML.

## Usage

```bash
linkedinto convert /path/to/LinkedInExport.zip
```

This parses the LinkedIn export and outputs `resume.json` (JSON Resume) and `rendercv.yaml` (RenderCV YAML) in the current directory.

### Options

| Flag                   | Description                                                 |
| ---------------------- | ----------------------------------------------------------- |
| `--output-dir`, `-o`   | Output directory (default: `.`)                             |
| `--jsonresume-only`    | Only output JSON Resume (skip RenderCV)                     |
| `--rendercv-only`      | Only output RenderCV YAML (skip JSON Resume)                |
| `--partial-jsonresume` | Path to existing JSON Resume for merging                    |
| `--partial-rendercv`   | Path to existing RenderCV YAML for merging                  |
| `--bullets`            | Custom bullet characters, pipe-separated (e.g. `"•\|*-\|"`) |
| `--verbose`, `-v`      | Enable debug logging                                        |

### Partial Overwrites

Use `--partial-jsonresume` or `--partial-rendercv` to merge data from an existing resume file. Fields from the partial file take precedence over the LinkedIn export data — useful for supplementing data LinkedIn doesn't export (e.g. professional summary, custom sections).

## What It Converts

| LinkedIn Section | JSON Resume      | RenderCV                  |
| ---------------- | ---------------- | ------------------------- |
| Profile          | `basics`         | `cv.sections`             |
| Positions        | `work`           | `cv.education` (internal) |
| Education        | `education`      | `cv.education`            |
| Skills           | `skills`         | `cv.skills`               |
| Languages        | `languages`      | `cv.skills`               |
| Projects         | `projects`       | `cv.sections`             |
| Publications     | `publications`   | `cv.sections`             |
| Certifications   | `certifications` | `cv.sections`             |
| Honors & Awards  | `awards`         | `cv.sections`             |
| Recommendations  | —                | —                         |
| Interests        | `interests`      | `cv.sections`             |
| Volunteer        | `volunteer`      | `cv.sections`             |

## Development

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [prek](https://prek.j178.dev/) (git hook runner)

### Setup

```bash
uv sync
uv run prek install
```

### Quality

```bash
# Lint, format check, type check, tests
uv run ruff check src/ tests/
uv run ruff format --check src/
uv run python -m ty check src/ tests/
uv run pytest
```

### Pre-commit Hooks

This project uses [prek](https://prek.j178.dev/) to run:

- `ruff check` — linting
- `ruff format` — formatting
- `ty check` — type checking

## License

MIT
