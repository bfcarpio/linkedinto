---
status: in-progress
phase: 1
updated: 2026-07-05
---

# Implementation Plan

## Goal

Replace hand--written RenderCV models with official `rendercv` package types, implement a generic URL-to-service classifier, update the TIOBE index, and implement a `linkedinto.toml` configuration file for global overrides.

## Context & Decisions

| Decision                          | Rationale                                                                              | Source                      |
| --------------------------------- | -------------------------------------------------------------------------------------- | --------------------------- |
| Use `rendercv` Pydantic v2 models | Ensures compatibility and type safety with official schema                             | `ref:research-rendercv-api` |
| Generic Service ID `twitterx`     | Unified identifier for X/Twitter to be formatted per-converter                         | User Request                |
| No URL Deduplication              | Preserve all found links as requested                                                  | User Request                |
| YAML Output Only                  | Rendering PDFs is outside the current tool scope                                       | User Request                |
| Python $\ge 3.12$                 | `rendercv` requires $\ge 3.12$; user preferred 3.11 but constraint is the package      | User Request                |
| Update TIOBE Index                | Keep local language popularity rankings current as of 2026-07-05                       | User Request                |
| `linkedinto.toml` config          | Provides a single point for overriding TIOBE and user identity data across all formats | User Request                |
| Highest Priority Overrides        | Config overrides must take precedence over extracted LinkedIn data                     | User Request                |

## Phase 1: Core Dependency & Type Migration [IN PROGRESS]

- [ ] **1.1 Update `pyproject.toml` (add `rendercv`, set `requires-python = ">=3.12"`, update `target-version`)** ← CURRENT
- [ ] 1.2 Remove `src/linkedinto/models_rendercv.py`
- [ ] 1.3 Update `src/linkedinto/converter_rendercv.py` to use official `Cv` and `Section` models
- [ ] 1.4 Adjust converter logic to match `Cv.sections` dict structure

## Phase 2: Configuration System (`linkedinto.toml`) [PENDING]

- [ ] 2.1 Define the `linkedinto.toml` schema (TIOBE overrides, identity overrides: name, email, phone, etc.)
- [ ] 2.2 Implement a config loader to parse `linkedinto.toml` if it exists
- [ ] 2.3 Integrate config overrides into the data pipeline to ensure they have highest priority over extracted data

## Phase 3: Generic Website Classification [PENDING]

- [ ] 3.1 Implement `classify_website(url: str) -> str | None` in `src/linkedinto/url_extractor.py`
- [ ] 3.2 Map `x.com` and `twitter.com` → `twitterx`
- [ ] 3.3 Ensure handling of varied URL formats and `None` for unknown services

## Phase 4: Converter Integration [PENDING]

- [ ] 4.1 Update `src/linkedinto/converter_jsonresume.py` to map `twitterx` → `twitter`
- [ ] 4.2 Update `src/linkedinto/converter_rendercv.py` to map `twitterx` → `X`
- [ ] 4.3 Ensure the config overrides from Phase 2 are applied to both converters
- [ ] 4.4 Verify no URL deduplication occurs during classification/population

## Phase 5: TIOBE Index Update [PENDING]

- [ ] 5.1 Update the TIOBE index file with the provided 2026-07-05 rankings
- [ ] 5.2 Add a comment to the index file indicating the date of the update
- [ ] 5.3 Ensure the `linkedinto.toml` TIOBE override logic correctly replaces these values

## Phase 6: Verification [PENDING]

- [ ] 6.1 Run existing test suite for regressions
- [ ] 6.2 Add tests for official model validation and `x. com`/`twitter.com` classification as `twitterx`
- [ ] 6.3 Add tests for `linkedinto. tom` overrides (identity and TIOBE)
- [ ] 6.4 Verify preservation of duplicate URLs in final output
- [ ] 6.5 Run linting and type-checking

## Notes

- 2026-07-05: `rendercv` package requires Python 3.12+, so we cannot go down to 3.11.
- 2026-07-05: User requested `twitterx` as the internal key for X/Twitter.
- 2026-07-05: Added `linkedinto. toml` for high-priority overrides of TIOBE and contact info.
