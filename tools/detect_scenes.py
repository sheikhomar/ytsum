from pathlib import Path

from ytsum.scene_detection.adaptive import AdaptiveSceneDetector
from ytsum.scene_detection.common import SceneDetectionResult
from ytsum.scene_detection.eval import SceneDetectionEvaluator, VideoSceneAnnotation


def run_and_evaluate_adaptive_detector(
    video_dir: Path,
    threshold: float = 2.5,
    min_scene_length_secs: float = 1,
    min_content_value: int = 5,
) -> None:
    detector_result_file_path = (
        video_dir
        / f"scene-detection-result-threshold{threshold:0.4f}-minlen{min_scene_length_secs:0.4f}-mincontent{min_content_value}.json"
    )

    if not detector_result_file_path.exists():
        video_file_paths = list(video_dir.glob("*.mp4"))
        if len(video_file_paths) != 1:
            print(
                f"Expected 1 video file in {video_dir}. But found {len(video_file_paths)} files."
            )
            return

        video_file_path = video_file_paths[0]

        detector = AdaptiveSceneDetector(
            adaptive_threshold=threshold,
            min_scene_length_secs=min_scene_length_secs,
            min_content_value=min_content_value,
        )
        result = detector.run(video_file_path=video_file_path)

        detector_result_file_path.write_text(result.model_dump_json(indent=2))
    else:
        result = SceneDetectionResult.model_validate_json(
            json_data=detector_result_file_path.read_text()
        )

    annotation_file_path = video_dir / "scene-annotation.json"
    if annotation_file_path.exists():
        print(f"Evaluating {result.video_file_path} with {annotation_file_path}...")
        annotation = VideoSceneAnnotation.model_validate_json(
            json_data=annotation_file_path.read_text()
        )

        evaluator = SceneDetectionEvaluator(tolerance_secs=1.5)

        evaluation_result = evaluator.run(annotation=annotation, result=result)

        print(evaluation_result.model_dump_json(indent=2))


def run_eval_only(video_dir: Path) -> None:
    annotation_file_path = video_dir / "scene-annotation.json"
    if annotation_file_path.exists():
        result_file_paths = video_dir.glob("scene-detection-result-*.json")
        for result_file_path in result_file_paths:
            result = SceneDetectionResult.model_validate_json(
                json_data=result_file_path.read_text()
            )

            print(f"Evaluating {result.video_file_path} with {annotation_file_path}...")
            annotation = VideoSceneAnnotation.model_validate_json(
                json_data=annotation_file_path.read_text()
            )

            evaluator = SceneDetectionEvaluator(tolerance_secs=1.5)

            evaluation_result = evaluator.run(annotation=annotation, result=result)

            print(evaluation_result.model_dump_json(indent=2))


def main() -> None:
    video_dir = Path("data/downloads")
    video_ids = ["Onf1UqKPMR4", "MBdEWLqfdms", "4gcGkFAG7OA"]

    run_eval_only(video_dir=video_dir / "4gcGkFAG7OA")

    for content_val in [1, 3, 5, 7, 9, 10]:
        for threshold in [0.5, 1.0, 2.0, 2.5, 3.0, 3.5]:
            for video_id in video_ids:
                run_and_evaluate_adaptive_detector(
                    video_dir=video_dir / video_id,
                    threshold=threshold,
                    min_scene_length_secs=1,
                    min_content_value=content_val,
                )


if __name__ == "__main__":
    main()
