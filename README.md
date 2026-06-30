# jsonprofile

Multi-language implementations of jsonprofile.

## Repository layout

- `python/`: Python package and tests.
- `java/`: Java package and tests.
- `shared/`: language-neutral schemas, fixtures, and conformance cases.
- `docs/`: project documentation.
- `.github/`: CI workflows.

## Development

Root commands are defined in `justfile`.

```sh
just test
just lint
just build
just clean
```

Implementation-specific commands are also available:

```sh
just test-python
just build-python
just test-java
just build-java
```

All local caches and build outputs are routed under `.cache/`.

## Implementation status

- Python: package skeleton with shared conformance smoke test.
- Java: Gradle skeleton with shared conformance smoke test.
- Shared contract: initial schema, fixtures, and smoke manifest.
