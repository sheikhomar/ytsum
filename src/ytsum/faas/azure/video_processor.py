import os
from typing import cast

import azure.durable_functions as durable_func
import azure.functions as func
from pydantic import BaseModel

from ytsum.faas.azure.video_download import (
    DownloadYouTubeVideoOutput,
    YouTubeVideoDownloadProcessor,
)
from ytsum.storage.azure import AzureBlobStorage

blueprint = durable_func.Blueprint()


class ProcessVideoInput(BaseModel):
    video_id: str


@blueprint.route(route="workflows/process-video/start/{video_id}")
@blueprint.durable_client_input(client_name="client")
async def start_workflow(
    req: func.HttpRequest,
    client: durable_func.DurableOrchestrationClient,
) -> func.HttpResponse:
    """
    Starts a new video processing workflow.

    This is an HTTP-triggered function that starts an instance of the Durable
    Functions orchestration function for processing a YouTube video. It expects
    a YouTube video ID in the route parameters and returns a check status response.

    Args:
        req: The HTTP request object.
        client: The Durable Functions client object.
    """
    video_id = req.route_params.get("video_id")
    if not video_id or len(video_id.strip()) < 5:
        return func.HttpResponse(
            f"The provided YouTube video ID: {video_id} is not valid.", status_code=400
        )

    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    if not azure_storage_conn_str:
        return func.HttpResponse(
            "Connection string to Azure Storage Account not found", status_code=500
        )

    input = ProcessVideoInput(video_id=video_id)

    instance_id = await client.start_new(
        orchestration_function_name=process_video.__name__,
        instance_id=video_id,
        client_input=input,
    )
    return client.create_check_status_response(request=req, instance_id=instance_id)


@blueprint.route(route="workflows/process-video/status/{video_id}")
@blueprint.durable_client_input(client_name="client")
async def get_workflow_status(
    req: func.HttpRequest,
    client: durable_func.DurableOrchestrationClient,
) -> func.HttpResponse:
    """
    Gets the status of a video processing workflow.

    This is an HTTP-triggered function that gets the status of an instance of the
    Durable Functions orchestration function for processing a YouTube video. It expects
    a YouTube video ID in the route parameters and returns the status of the workflow.

    Args:
        req: The HTTP request object.
        client: The Durable Functions client object.
    """
    video_id = req.route_params.get("video_id")
    if not video_id or len(video_id.strip()) < 5:
        return func.HttpResponse(
            f"The provided YouTube video ID: {video_id} is not valid.", status_code=400
        )

    return client.create_check_status_response(request=req, instance_id=video_id)


@blueprint.orchestration_trigger(context_name="context")
def process_video(context: durable_func.DurableOrchestrationContext):
    input = cast(ProcessVideoInput, context.get_input())

    download_result: DownloadYouTubeVideoOutput = yield context.call_activity(
        name="download_youtube_video",
        input_=input.video_id,
    )

    if download_result.failed:
        return [download_result]

    mp4_file_paths = [
        file_path
        for file_path in download_result.saved_file_paths
        if file_path.endswith(".mp4")
    ]
    if len(mp4_file_paths) == 1:
        download_result.error_message = "No MP4 files found after download."
        return [download_result]

    video_file_path = mp4_file_paths[0]
    extracted_frames = yield context.call_activity(
        name="extract_frames",
        input_=video_file_path,
    )

    return [download_result, extracted_frames]


@blueprint.activity_trigger(input_name="videoId")
async def download_youtube_video(videoId: str) -> DownloadYouTubeVideoOutput:
    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    blob_storage = AzureBlobStorage(
        connection_string=azure_storage_conn_str,
        container_name="youtube-videos",
    )

    processor = YouTubeVideoDownloadProcessor(
        video_id=videoId, blob_storage=blob_storage
    )
    output = await processor.run()
    return output


@blueprint.activity_trigger(input_name="videoFilePath")
async def extract_frames(videoFilePath: str) -> str:
    return videoFilePath
