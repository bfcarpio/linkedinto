# linkedinto

Convert a LinkedIn export ZIP to [JSON Resume](https://jsonresume.org/), [RenderCV](https://rendercv.com/) YAML, and [Awesome-CV](https://github.com/posquit0/Awesome-CV) LaTeX.

## Usage

```bash
linkedinto convert /path/to/LinkedInExport.zip
```

This parses the LinkedIn export and outputs `resume.json` (JSON Resume), `rendercv.yaml` (RenderCV YAML), and `awesome-cv.tex` (Awesome-CV LaTeX) in the current directory.

### Options

| Flag                      | Description                                                 |
| ------------------------- | ----------------------------------------------------------- |
| `--output-dir`, `-o`      | Output directory (default: `.`)                             |
| `--jsonresume-only`       | Only output JSON Resume (skip RenderCV and Awesome-CV)       |
| `--rendercv-only`         | Only output RenderCV YAML (skip JSON Resume and Awesome-CV) |
| `--awesomecv-only`        | Only output Awesome-CV LaTeX (skip JSON Resume and RenderCV)|
| `--partial-jsonresume`    | Path to existing JSON Resume for merging                    |
| `--partial-rendercv`      | Path to existing RenderCV YAML for merging                  |
| `--partial-awesomecv`     | Path to existing Awesome-CV .tex (not yet supported)         |
| `--bullets`               | Custom bullet characters, pipe-separated (e.g. `"•\|*-\|"`) |
| `--verbose`, `-v`         | Enable debug logging                                        |
| `--ai-group`              | Use AI to group skills into logical categories (requires `[ai]` config) |
| `--ai-preview`            | Print AI skill groupings to stdout and exit (implies `--ai-group`) |
| `--ai-model`              | Override the model from `[ai]` config                       |
| `--no-cache`              | Bypass the skill-grouping disk cache                        |

### Partial Overwrites

Use `--partial-jsonresume` or `--partial-rendercv` to merge data from an existing resume file.

### Configuration

Copy the example config:
```bash
cp linkedinto.toml.example linkedinto.toml
```

Edit `linkedinto.toml` to customize:
- Profile override fields (name, email, location)
- TIOBE language override
- [ai] section for AI skill grouping (model, api_key, skill_groups presets)

Fields from the partial file take precedence over the LinkedIn export data — useful for supplementing data LinkedIn doesn't export (e.g. professional summary, custom sections).

| LinkedIn Section       | JSON Resume       | RenderCV                  | Awesome-CV                |
| ---------------------- | ----------------- | ------------------------- | ------------------------- |
| Profile                | `basics`          | `cv.sections`             | `\name`, `\position`      |
| Positions              | `work`            | `cv.experience`           | `\cvsection{Experience}`   |
| Education              | `education`       | `cv.education`            | `\cvsection{Education}`   |
| Skills                 | `skills`          | `cv.skills`               | `\cvsection{Skills}`      |
| Languages              | `languages`       | `cv.languages`            | `\cvsection{Languages}`   |
| Projects               | `projects`        | `cv.sections`             | `\cvsection{Projects}`    |
| Publications           | `publications`    | `cv.sections`             | `\cvsection{Publications}`|
| Certifications         | `certifications`  | `cv.sections`             | `\cvsection{Certifications}` |
| Honors & Awards        | `awards`          | `cv.sections`             | `\cvsection{Honors}`      |
| Recommendations        | —                 | —                         | —                         |
| Interests              | `interests`       | `cv.sections`             | `\cvsection{Interests}`   |
| Volunteer              | `volunteer`       | `cv.sections`             | `\cvsection{Volunteer}`   |

## AI Skill Grouping

Linkedinto can use AI to automatically categorize your skills into logical groups based on your LinkedIn profile data. The pipeline includes:

1. **Config presets** - Define skill grouping categories and approve them before conversion
2. **TIOBE/Pygments detection** - Detect programming languages via TIOBE top-50 + Pygments fallback (never sent to LLM)
3. **Disk cache** - Cache LLM results at `~/.cache/linkedinto/skill-groups.json`
4. **LLM processing** - Group categories (requires AI model from `[ai]` config)

**Output per converter:**
- **RenderCV**: Programming languages go to a dedicated `technologies` section; other skills become categorized `skills` entries
- **JSON Resume**: All skills become categorized `skills` array as `Skill(name=category, keywords=[...])`

**Usage:**
```bash
# Set up the config
cp linkedinto.toml.example linkedinto.toml
# Add [ai] section with model and optional api_key or LINKEDINTO_AI_API_KEY env var
uv sync --extra ai

# Preview AI groupings before converting
linkedinto convert export.zip --ai-preview

# Enable AI grouping during conversion
linkedinto convert export.zip --ai-group

# Override model from config
linkedinto convert export.zip --ai-group --ai-model gpt-4
```

**Example `linkedinto.toml` config:**
```toml
[ai]
model = "gpt-4"
api_key = "sk-..."  # or use LINKEDINTO_AI_API_KEY environment variable

[ai.skill_groups]
# Presets for skill categories
common = ["Communication", "Teamwork", "Problem Solving"]
hard = ["Project Management", "DevOps", "Database Design"]
```

**To enable AI grouping during development:**
```bash
# After initial setup
uv sync --extra ai
```

## Development

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [prek](https://prek.j178.dev/) (git hook runner)

### Setup

```bash
uv sync --extra ai
uv run prek install
```

### Quality

```bash
# Lint, format check, type check, tests
uv run ruff check src/ tests/ packages/
uv run ruff format --check src/ packages/
uv run ty check src/ tests/ packages/
uv run pytest
```

### Pre-commit Hooks

This project uses [prek](https://prek.j178.dev/) to run:

- `ruff check` — linting
- `ruff format` — formatting
- `ty check` — type checking


## Plugin Architecture

Each converter is an independently-installable package, discovered at runtime via Python entry points (`linkedinto.converters` group):

| Package | Entry point | Output |
| ------- | ----------- | ------ |
| `linkedinto-jsonresume` | `jsonresume` | `resume.json` |
| `linkedinto-rendercv` | `rendercv` | `rendercv.yaml` |
| `linkedinto-awesomecv` | `awesomecv` | `awesome-cv.tex` |

All three are installed by default via the uv workspace. To add a new converter, create a package with a `linkedinto.converters` entry point — no core changes needed.

### Rendering Awesome-CV PDFs

The Awesome-CV converter produces `.tex` files. To compile to PDF, use the `render-pdf` mise task (requires [TinyTeX](https://yihui.org/tinytex/)):

```bash
mise install  # installs tinytex (provides xelatex)
cd /path/to/output-dir
mise run render-pdf
```

The task auto-installs required LaTeX packages via `tlmgr` and downloads `awesome-cv.cls` if missing. Awesome-CV requires `xelatex` (not `pdflatex`).

## License

MIT
