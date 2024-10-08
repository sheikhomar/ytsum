import os
import tempfile
from pathlib import Path
from typing import List

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from ytsum import say_hello
from ytsum.faas.azure.video_processor import blueprint as video_processor_blueprint
from ytsum.youtube import YouTubeVideoDownloader

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_functions(video_processor_blueprint)


def upload_files_in_dir_to_blob_container(
    file_paths: List[Path], connection_string: str, prefix: str, container_name: str
) -> List[str]:
    blob_service_client = BlobServiceClient.from_connection_string(
        conn_str=connection_string
    )
    container_client = blob_service_client.get_container_client(
        container=container_name
    )

    if not container_client.exists():
        container_client.create_container()

    uploaded_files = []
    for file in file_paths:
        blob_name = f"{prefix}/{file.name}"
        blob_client = container_client.get_blob_client(blob_name)
        with file.open("rb") as fh:
            blob_client.upload_blob(fh, overwrite=True)
        uploaded_files.append(blob_name)

    return uploaded_files


@app.function_name(name="HttpTrigger1")
@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
def main(req: func.HttpRequest) -> func.HttpResponse:
    output = "No calls to ytsum package."
    output = say_hello()
    return func.HttpResponse(body=output, status_code=200)


@app.function_name(name="YouTubeDownloader")
@app.route(route="download/{video_id}", auth_level=func.AuthLevel.ANONYMOUS)
def download(req: func.HttpRequest) -> func.HttpResponse:
    """Downloads YouTube video files and uploads them to a blob container.

    Args:
        req: The HTTP request object. Expected to contain a route parameter "video_id".

    Returns:
        An HTTP response indicating the result of the operation.
    """

    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    if not azure_storage_conn_str:
        return func.HttpResponse(
            "Connection string to Azure Storage Account not found", status_code=500
        )

    video_id = req.route_params.get("video_id")
    if not video_id or len(video_id.strip()) < 5:
        return func.HttpResponse(
            f"The provided YouTube video ID: {video_id} is not valid.", status_code=400
        )

    # Create a temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        downloader = YouTubeVideoDownloader(url=youtube_url, output_dir=output_dir)
        download_result = downloader.run()

        if download_result != 0:
            return func.HttpResponse(
                f"Failed to download video with ID: {video_id}", status_code=500
            )

        files = list(output_dir.glob("*"))
        if not files:
            return func.HttpResponse(
                f"No files found for video ID: {video_id}", status_code=404
            )

        uploaded_files = upload_files_in_dir_to_blob_container(
            file_paths=files,
            connection_string=azure_storage_conn_str,
            prefix=video_id,
            container_name="youtube-videos",
        )

        return func.HttpResponse(
            f"Successfully processed video {video_id}. Uploaded files: {', '.join(uploaded_files)}",
            status_code=200,
        )
