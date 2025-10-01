"""
融合判定モジュール
音声と映像の情報を統合して無呼吸イベントを精緻化
"""
import numpy as np
from typing import List, Dict, Tuple


def refine_with_motion(
    apnea_candidates: List[Dict],
    motion_t: np.ndarray,
    motion: np.ndarray,
    motion_threshold_percentile: int = 20
) -> List[Dict]:
    """
    動き量情報で無呼吸候補を精緻化

    Args:
        apnea_candidates: 音声ベースの無呼吸候補リスト
        motion_t: 動き量の時刻配列
        motion: 動き量配列
        motion_threshold_percentile: 動き量の閾値パーセンタイル

    Returns:
        精緻化された無呼吸イベントリスト
    """
    if len(motion_t) == 0 or len(motion) == 0:
        # 動き量データがない場合は音声候補をそのまま返す
        return apnea_candidates

    # 動き量閾値を計算
    motion_threshold = np.percentile(motion, motion_threshold_percentile)

    refined_events = []

    for candidate in apnea_candidates:
        start = candidate["start"]
        end = candidate["end"]

        # 候補区間内の動き量を取得
        mask = (motion_t >= start) & (motion_t <= end)
        motion_in_range = motion[mask]

        if len(motion_in_range) == 0:
            # 動き量データがない区間はそのまま採用
            refined_events.append(candidate)
            continue

        # 区間内の平均動き量
        avg_motion = np.mean(motion_in_range)

        # 低動き量の場合、信頼度を上げる
        if avg_motion < motion_threshold:
            confidence_boost = 0.3
            new_confidence = min(1.0, candidate["confidence"] + confidence_boost)

            refined_events.append({
                "start": candidate["start"],
                "end": candidate["end"],
                "confidence": new_confidence
            })
        else:
            # 動き量が高い場合は信頼度を下げる (誤検出の可能性)
            confidence_penalty = 0.2
            new_confidence = max(0.0, candidate["confidence"] - confidence_penalty)

            # 信頼度が低すぎる場合は除外
            if new_confidence >= 0.3:
                refined_events.append({
                    "start": candidate["start"],
                    "end": candidate["end"],
                    "confidence": new_confidence
                })

    return refined_events


def merge_nearby_events(events: List[Dict], max_gap: float = 2.0) -> List[Dict]:
    """
    近接するイベントを統合

    Args:
        events: イベントリスト
        max_gap: 統合する最大ギャップ (秒)

    Returns:
        統合されたイベントリスト
    """
    if len(events) == 0:
        return []

    # 開始時刻でソート
    sorted_events = sorted(events, key=lambda x: x["start"])

    merged = []
    current = sorted_events[0].copy()

    for event in sorted_events[1:]:
        gap = event["start"] - current["end"]

        if gap <= max_gap:
            # 統合
            current["end"] = event["end"]
            # 信頼度は平均を取る
            current["confidence"] = (current["confidence"] + event["confidence"]) / 2
        else:
            # 現在のイベントを確定し、次へ
            merged.append(current)
            current = event.copy()

    # 最後のイベント
    merged.append(current)

    return merged
