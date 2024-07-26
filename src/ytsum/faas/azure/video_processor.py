import os
from typing import Dict, Optional, cast

import azure.durable_functions as durable_func
import azure.functions as func
from azure.functions.decorators.function_app import FunctionBuilder
from pydantic import BaseModel, Field

from ytsum.faas.azure.helpers.frame_extraction import VideoFrameExtractor
from ytsum.faas.azure.video_download import (
    YouTubeVideoDownloadProcessor,
    YouTubeVideoDownloadProcessorResult,
)
from ytsum.storage.azure import AzureBlobStorage

blueprint = durable_func.Blueprint()


class ProcessVideoInput(BaseModel):
    video_id: str


class ProcessVideoOutput(BaseModel):
    video_id: str
    stage: str = Field(..., description="Which stage the workflow is currently at")
    error_message: Optional[str] = Field(default=None)


class ExtractFramesInput(BaseModel):
    video_id: str
    video_file_path: str


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

    func_name = cast(FunctionBuilder, process_video)._function._name

    instance_id = await client.start_new(
        orchestration_function_name=func_name,
        instance_id=video_id,
        client_input=input.model_dump(),
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
    # Step 1: Parse the input and validate it
    input = ProcessVideoInput.model_validate(obj=context.get_input())

    # Step 2: Call the `download_youtube_video`` activity function
    result_obj = yield context.call_activity(
        name="download_youtube_video",
        input_=input.video_id,
    )
    download_youtube_video_result = YouTubeVideoDownloadProcessorResult.model_validate(
        obj=result_obj
    )
    print(f"Download result: {download_youtube_video_result}")

    # Step 3: Check if the download was successful
    if download_youtube_video_result.failed:
        err_msg = download_youtube_video_result.error_message
        return ProcessVideoOutput(
            video_id=input.video_id,
            stage="download_youtube_video",
            error_message=f"Failed to download YouTube video: {err_msg}",
        ).model_dump()

    # Step 4: Check if any MP4 files were downloaded
    mp4_file_paths = [
        file_path
        for file_path in download_youtube_video_result.saved_file_paths
        if file_path.endswith(".mp4")
    ]
    if len(mp4_file_paths) != 1:
        return ProcessVideoOutput(
            video_id=input.video_id,
            stage="mp4_file_check",
            error_message=(
                "No MP4 files found after download. "
                f"Expected exactly 1 but found {len(mp4_file_paths)}."
            ),
        ).model_dump()

    # Step 5: Call the `extract_frames` activity function
    extracted_frames = yield context.call_activity(
        name="extract_frames",
        input_=ExtractFramesInput(
            video_id=input.video_id,
            video_file_path=mp4_file_paths[0],
        ).model_dump(),
    )
    print(f"Extracted frames: {extracted_frames}")

    # Final step: Return the completed status
    return ProcessVideoOutput(
        video_id=input.video_id,
        stage="completed",
    ).model_dump()


@blueprint.activity_trigger(input_name="videoId")
async def download_youtube_video(videoId: str) -> Dict[str, object]:
    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    blob_storage = AzureBlobStorage(
        connection_string=azure_storage_conn_str,
        container_name="youtube-videos",
    )

    processor = YouTubeVideoDownloadProcessor(video_id=videoId, storage=blob_storage)
    result = await processor.run()
    return result.model_dump()


@blueprint.activity_trigger(input_name="inputDict")
async def extract_frames(inputDict: Dict[str, object]) -> Dict[str, object]:
    input = ExtractFramesInput.model_validate(obj=inputDict)

    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    videos_store = AzureBlobStorage(
        connection_string=azure_storage_conn_str,
        container_name="youtube-videos",
    )

    output_store = AzureBlobStorage(
        connection_string=azure_storage_conn_str,
        container_name="extracted-frames",
    )

    processor = VideoFrameExtractor(
        video_id=input.video_id,
        video_file_path=input.video_file_path,
        input_storage=videos_store,
        output_storage=output_store,
    )
    result = await processor.run()

    return result.model_dump()
