# Tic Ton Python SDK

This is the Python SDK for Tic Ton Oracle on TON blockchain, which is a pure decentralized oracle protocol that can provide latest price with high precision guraranteed by incentive mechanism.


## Development Guide

### Install

1. Make sure [poetry](https://python-poetry.org/docs/#installation) installed on your machine.

    > you may need to set the `PATH` environment variable to include the Poetry binary directory, e.g. `export PATH="$HOME/.local/bin:$PATH"`

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. Install plugin for poetry

    ``` bash
    poetry self add poetry-bumpversion
    ```

3. Install dependencies

    ```bash
    make install
    ```

4. Start your virtual environment

    ```bash
    poetry shell
    ```

5. Run tests

    ```bash
    poetry run pytest
    ```

## Publish Guide

1. Update version in `pyproject.toml`

    ```bash
    make bump
    ```

2. Create a release on GitHub, once the release is created, the package will be published to PyPI automatically.