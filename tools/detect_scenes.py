from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from ytsum.scene_detection.adaptive import AdaptiveSceneDetector
from ytsum.scene_detection.common import SceneDetectionResult
from ytsum.scene_detection.eval import SceneDetectionEvaluator, VideoSceneAnnotation
from ytsum.scene_detection.ssim import StructuralSimilaritySceneDetector


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


def run_and_evaluate_ssim_detector(
    video_dir: Path,
    threshold: float,
    min_scene_length_secs: float,
) -> None:
    detector_result_file_path = (
        video_dir
        / f"scene-detection-result-ssim-threshold{threshold:0.4f}-minlen{min_scene_length_secs:0.4f}.json"
    )

    if not detector_result_file_path.exists():
        video_file_paths = list(video_dir.glob("*.mp4"))
        if len(video_file_paths) != 1:
            print(
                f"Expected 1 video file in {video_dir}. But found {len(video_file_paths)} files."
            )
            return

        video_file_path = video_file_paths[0]

        detector = StructuralSimilaritySceneDetector(
            threshold=threshold,
            min_scene_length_secs=min_scene_length_secs,
            sample_interval_secs=0.5,
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


def generate_plot(df_data: pd.DataFrame, output_path: Path) -> None:
    print(df_data)

    pivot_table = pd.pivot_table(
        df_data,
        values="recall",
        index="adaptive_threshold",
        columns=["min_content_value", "min_scene_length_secs"],
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(pivot_table, annot=True, fmt=".2f", cmap="viridis", ax=ax)
    ax.set_title("Scene Detection Recall Heatmap")
    ax.set_xlabel("Min Content Value & Min Scene Length (secs)")
    ax.set_ylabel("Adaptive Threshold")
    fig.savefig(output_path)
    print(f"Saved plot to {output_path}")


def run_eval_only(video_dir: Path) -> None:
    annotation_file_path = video_dir / "scene-annotation.json"
    if annotation_file_path.exists():
        result_file_paths = video_dir.glob("scene-detection-result-*.json")

        raw_data = []

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

            raw_data.append(
                {
                    "adaptive_threshold": result.adaptive_threshold,
                    "min_scene_length_secs": result.min_scene_length_secs,
                    "min_content_value": result.min_content_val,
                    "accuracy": evaluation_result.accuracy,
                    "precision": evaluation_result.precision,
                    "recall": evaluation_result.recall,
                    "f1_score": evaluation_result.f1_score,
                }
            )

        df_data = pd.DataFrame(raw_data)
        generate_plot(df_data, video_dir / "results.png")


def main() -> None:
    video_dir = Path("data/downloads")
    video_ids = ["Onf1UqKPMR4", "MBdEWLqfdms", "4gcGkFAG7OA"]

    run_eval_only(video_dir=video_dir / "4gcGkFAG7OA")
    return

    for threshold in [0.98, 0.96, 0.95, 0.94, 0.90]:
        for len in [1, 2, 3, 4, 5]:
            run_and_evaluate_ssim_detector(
                video_dir=video_dir / "4gcGkFAG7OA",
                threshold=threshold,
                min_scene_length_secs=len,
            )

    for content_val in [2, 4, 6]:
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
