<!-- Stress test mention: this comment verifies @mention handling during concurrent pipelines -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `countdown.sh`: `--tick-format MODE` flag controlling how the ticker renders the remaining time. Accepted modes: `seconds` (default — preserves existing output), `mm-ss` (zero-padded `MM:SS`), and `human` (compact `1m 30s`). Invalid values fail fast with a stderr error before the countdown starts. Omitting the flag keeps the current output unchanged.

### Changed

### Deprecated

### Removed

### Fixed

### Security
