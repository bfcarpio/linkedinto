# linkedinto

Convert a LinkedIn export ZIP to [JSON Resume](https://jsonresume.org/) and [RenderCV](https://rendercv.com/) YAML.

## Usage

```bash
linkedinto convert /path/to/LinkedInExport.zip
```

This parses the LinkedIn export and outputs `resume.json` (JSON Resume) and `rendercv.yaml` (RenderCV YAML) in the current directory.

### Options

| Flag                      | Description                                                 |
| ------------------------- | ----------------------------------------------------------- |
| `--output-dir`, `-o`      | Output directory (default: `.`)                             |
| `--jsonresume-only`       | Only output JSON Resume (skip RenderCV)                     |
| `--rendercv-only`         | Only output RenderCV YAML (skip JSON Resume)                |
| `--partial-jsonresume`    | Path to existing JSON Resume for merging                    |
| `--partial-rendercv`     | Path to existing RenderCV YAML for merging                  |
| `--bullets`               | Custom bullet characters, pipe-separated (e.g. `"•\|*-\|"`) |
| `--verbose`, `-v`         | Enable debug logging                                        |
| `--ai-group`              | Use AI to group skills into logical categories (requires `[ai]` config) |
| `--ai-preview`            | Print AI skill groupings to stdout and exit (implies `--ai-group`) |
| `--ai-model`              | Override the model from `[ai]` config                       |
| `--no-cache`              | Bypass the skill-grouping disk cache                      |

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

## What It Converts

| LinkedIn Section       | JSON Resume       | RenderCV                  |
| ---------------------- | ----------------- | ------------------------- |
| Profile                | `basics`          | `cv.sections`             |
| Positions              | `work`            | `cv.experience`           |
| Education              | `education`       | `cv.education`            |
| Skills                 | `skills`          | `cv.skills`               |
| Languages              | `languages`       | `cv.languages`            |
| Projects               | `projects`        | `cv.sections`             |
| Publications           | `publications`    | `cv.sections`             |
| Certifications         | `certifications`  | `cv.sections`             |
| Honors & Awards        | `awards`          | `cv.sections`             |
| Recommendations        | —                 | —                         |
| Interests              | `interests`       | `cv.sections`             |
| Volunteer              | `volunteer`       | `cv.sections`             |

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
# With AI skill grouping support
uv sync --extra ai
uv run prek install
```

# With AI skill grouping support
uv sync --extra ai
uv run prek install
```

### Quality

```bash
# Lint, format check, type check, tests
uv run ruff check src/ tests/
uv run ruff format --check src/
uv run ty check src/ tests/
uv run pytest
```

### Pre-commit Hooks

This project uses [prek](https://prek.j178.dev/) to run:

- `ruff check` — linting
- `ruff format` — formatting
- `ty check` — type checking

## License

MIT
