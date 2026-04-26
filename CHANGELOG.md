<!-- Stress test mention: this comment verifies @mention handling during concurrent pipelines -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

### Changed

- `countdown.sh` now renders the live remaining time as `H:MM:SS` (≥ 1 hour),
  `M:SS` / `MM:SS` (≥ 1 minute), or bare seconds (< 1 minute) instead of
  `Xs`. The `Time remaining: ` label, `--silent`, `--help`, validation, and
  the final `Time's up!` line are unchanged.

### Deprecated

### Removed

### Fixed

### Security
