# Setup Spec Kitty Action

GitHub Action to install `spec-kitty-cli` with caching and optional testing dependencies.

## Features

- 🚀 **Fast installation** with pip caching
- 🐍 **Flexible Python versions** (default: 3.12)
- 🧪 **Optional test dependencies** (pytest, pytest-timeout, pytest-xdist)
- 🔬 **Optional mutmut** for mutation testing
- 📌 **Version pinning** support
- ✅ **Installation verification**

## Usage

### Basic Usage

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Spec Kitty
    uses: ./.github/actions/setup-spec-kitty
  
  - name: Use spec-kitty
    run: spec-kitty --version
```

### With Test Dependencies

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Spec Kitty with test deps
    uses: ./.github/actions/setup-spec-kitty
    with:
      install-test-deps: true
  
  - name: Run tests
    run: pytest tests/
```

### With Mutation Testing

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Spec Kitty with mutmut
    uses: ./.github/actions/setup-spec-kitty
    with:
      install-test-deps: true
      install-mutmut: true
  
  - name: Run mutation tests
    run: mutmut run
```

### With Version Pinning

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup specific Spec Kitty version
    uses: ./.github/actions/setup-spec-kitty
    with:
      spec-kitty-version: '0.16.2'
```

### Custom Python Version

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Spec Kitty with Python 3.11
    uses: ./.github/actions/setup-spec-kitty
    with:
      python-version: '3.11'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `python-version` | Python version to use | No | `3.12` |
| `install-test-deps` | Install test dependencies (pytest, pytest-timeout, pytest-xdist) | No | `false` |
| `install-mutmut` | Install mutmut for mutation testing | No | `false` |
| `spec-kitty-version` | Specific version to install (e.g., "0.16.2" or "latest") | No | `latest` |
| `cache-dependency-path` | Path to dependency file for cache key | No | Auto-detect `pyproject.toml` |

## Outputs

| Output | Description |
|--------|-------------|
| `cache-hit` | Whether pip cache was hit (`true` or `false`) |
| `spec-kitty-version` | Installed version of spec-kitty-cli |

## Using Outputs

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Spec Kitty
    id: setup-spec-kitty
    uses: ./.github/actions/setup-spec-kitty
  
  - name: Check cache status
    run: |
      echo "Cache hit: ${{ steps.setup-spec-kitty.outputs.cache-hit }}"
      echo "Installed version: ${{ steps.setup-spec-kitty.outputs.spec-kitty-version }}"
```

## Cache Strategy

The action caches:
- `~/.cache/pip` - pip download cache
- `~/.local/lib/python{version}/site-packages` - installed packages

Cache key is based on:
1. Operating system (e.g., `Linux`, `macOS`, `Windows`)
2. Python version (e.g., `3.12`)
3. Hash of dependency file (`pyproject.toml` by default)

This ensures fast subsequent runs while invalidating cache when dependencies change.

## Performance

**Without cache** (first run): ~60-90 seconds
**With cache** (subsequent runs): ~10-15 seconds

⏱️ **Time saved**: ~75 seconds per workflow run

## Development

To test locally (requires `act` or similar):

```bash
# Test basic installation
act -j test-action

# Test with mutmut
act -j test-action -e test/events/mutmut.json
```

## Contributing

When updating the action:
1. Update `action.yml` with new features
2. Update this README with usage examples
3. Test in a real workflow
4. Document breaking changes in CHANGELOG.md

## License

Same as spec-kitty-cli (see root LICENSE file)
