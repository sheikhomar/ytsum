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

6. Install [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) to develop and test Azure Functions locally.

   You can start the function app by running:

   ```bash
   func start
   ```

## Deployment

### Azure Deployment

In order to deploy Azure resources via GitHub Actions, you must setup deployment credentials in Azure and create secrets in GitHub. [This guide](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-github-actions) provides a step-by-step process to deploy Bicep files using GitHub Actions. You can find an [offline version of the guide](docs/deployment/deploy-bicep-from-github.pdf) in the `docs/deployment` directory.

Here are the steps needed to deploy Azure resources via GitHub Actions:

1. Bootstrap Azure:

   ```sh
   deploy/azure/bootstrap.sh
   ```

   This script creates a resource group and generates a service principle that can be used to deploy via GitHub Actions. The credentials are saved to a file: `.secrets/service-principal-credentials.json`.

2. Configure GitHub Repository Secrets
   1. In [GitHub](https://github.com/), navigate to your repository.
   2. Select **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
   3. Create a new secret named `AZURE_CREDENTIALS` and add the contents of the `.secrets/service-principal-credentials.json` file.
   4. Create a secret `AZURE_SUBSCRIPTION` and copy the subscription ID from the file in step 1.
   5. Create a secret `AZURE_RG` and specify the resource group name (example: `bb-ytsum-weu-dev-rg`).
