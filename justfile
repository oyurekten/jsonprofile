set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

export PRE_COMMIT_HOME := ".cache/pre-commit"
export UV_CACHE_DIR := ".cache/uv"
export GRADLE_USER_HOME := ".cache/gradle"

test: test-python test-java

lint:
    uv --project python run pre-commit run --all-files
    cd python && uv run ruff check src tests

build: build-python build-java

clean:
    rm -rf .cache/python .cache/java .cache/gradle .cache/uv .cache/pre-commit

test-python:
    cd python && uv run pytest

test-java:
    gradle --project-cache-dir .cache/gradle/project-cache -p java test

build-python:
    cd python && uv build --out-dir ../.cache/python/dist --clear

build-java:
    gradle --project-cache-dir .cache/gradle/project-cache -p java build
