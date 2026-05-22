from __future__ import annotations


def scope_allows_accuracy_claim(dataset_scope: object) -> bool:
    if not isinstance(dataset_scope, str):
        return False
    return dataset_scope in {"imagenet_val", "imagenet_validation"} or dataset_scope.startswith(
        "scoped_subset:"
    )


def accuracy_report(
    *,
    manifest: dict[str, object],
    predictions: dict[str, object],
    manifest_by_id: dict[str, dict[str, object]],
    total: int,
    top1_correct: int,
    top5_correct: int,
    missing_predictions: list[str],
    extra_predictions: list[str],
) -> dict[str, object]:
    complete = not missing_predictions and not extra_predictions
    dataset_scope = manifest.get("dataset_scope", "unknown")
    return {
        "schema_version": 1,
        "target": predictions.get("target", "apple/mobilevit-small"),
        "dataset_scope": dataset_scope,
        "image_count": len(manifest_by_id),
        "evaluated_count": total,
        "top1_correct": top1_correct,
        "top5_correct": top5_correct,
        "top1_accuracy": top1_correct / total if total else 0.0,
        "top5_accuracy": top5_correct / total if total else 0.0,
        "complete_prediction_set": complete,
        "missing_predictions": missing_predictions,
        "extra_predictions": extra_predictions,
        "accuracy_claim_allowed": (
            complete
            and total == len(manifest_by_id)
            and total > 0
            and scope_allows_accuracy_claim(dataset_scope)
        ),
    }
