from pathlib import Path

from ytsum.scene_detection.adaptive import AdaptiveSceneDetector
from ytsum.scene_detection.eval import SceneDetectionEvaluator, VideoSceneAnnotation


def run_and_evaluate_adaptive_detector(
    video_dir: Path,
    threshold: float = 2.5,
    min_scene_length_secs: float = 1,
    min_content_value: int = 5,
) -> None:
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

    annotation_file_path = video_dir / "scene-annotation.json"
    if annotation_file_path.exists():
        print(f"Evaluating {video_file_path} with {annotation_file_path}...")
        annotation = VideoSceneAnnotation.model_validate_json(
            json_data=annotation_file_path.read_text()
        )

        evaluator = SceneDetectionEvaluator(tolerance_secs=1.5)

        evaluation_result = evaluator.run(annotation=annotation, result=result)

        print(evaluation_result.model_dump_json(indent=2))


def main() -> None:
    video_dir = Path("data/downloads")

    # run_and_evaluate_adaptive_detector(video_dir=video_dir / "Onf1UqKPMR4")
    # run_and_evaluate_adaptive_detector(video_dir=video_dir / "MBdEWLqfdms")
    run_and_evaluate_adaptive_detector(
        video_dir=video_dir / "4gcGkFAG7OA",
        threshold=2.5,
        min_scene_length_secs=1,
        min_content_value=5,
    )


if __name__ == "__main__":
    main()
