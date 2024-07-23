import tempfile
from pathlib import Path
from typing import List

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from ytsum import say_hello
from ytsum.youtube import YouTubeVideoDownloader

app = func.FunctionApp()


def get_blob_connection_string() -> str:
    """
    Retrieve the blob storage connection string from environment variables.

    :return: The connection string for blob storage.
    """
    import os

    connection_string = os.environ.get("AzureWebJobsStorage")
    if not connection_string:
        raise ValueError(
            "Blob storage connection string not found in environment variables."
        )
    return connection_string


def upload_files_in_dir_to_blob_container(
    file_paths: List[Path], prefix: str, container_name: str = "youtube-videos"
) -> List[str]:
    connection_string = get_blob_connection_string()
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
            prefix=video_id,
            container_name="youtube-videos",
        )

        return func.HttpResponse(
            f"Successfully processed video {video_id}. Uploaded files: {', '.join(uploaded_files)}",
            status_code=200,
        )
