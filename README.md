# YouTube Summarizer

A Python project focused on summarizing YouTube videos.


## Development Setup

1. Ensure [pyenv](https://github.com/pyenv/pyenv) and [PDM](https://pdm.fming.dev/) are installed.

2. Install the correct Python version:

    ```bash
    pyenv install --skip-existing
    ```

3. Install the dependencies:

    ```bash
    pdm install
    pdm run python -m ensurepip
    ```

4. Install the pre-commit hooks:

    ```bash
    pdm run pre-commit install
    ```

5. Create `.env` file by copying the `.env.template` file and updating the values as needed:

    ```bash
    cp .env.template .env
    ```
