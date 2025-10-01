"""
E2Eテスト
システム全体の動作を確認
"""
import pytest
import sys
from pathlib import Path
import numpy as np
import cv2
import subprocess
import time

# モジュールパスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services import audio, video, analyzer, storage


# テスト用の短いダミー動画を生成
def create_test_video(output_path: str, duration_sec: int = 30, fps: int = 10):
    """テスト用のダミー動画を生成"""
    width, height = 640, 480

    # VideoWriter準備
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 音声付き動画生成用に一度フレームだけ書き出し
    num_frames = duration_sec * fps

    for i in range(num_frames):
        # シンプルなグレーのフレーム
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128

        # フレーム番号を描画
        cv2.putText(frame, f"Frame {i}", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        out.write(frame)

    out.release()

    # FFmpegで無音の音声トラックを追加
    temp_path = output_path + ".temp.mp4"
    cmd = [
        'ffmpeg', '-i', output_path,
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=16000',
        '-c:v', 'copy', '-c:a', 'aac', '-shortest',
        '-y', temp_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        # 元のファイルを置き換え
        Path(output_path).unlink()
        Path(temp_path).rename(output_path)
    except Exception as e:
        print(f"警告: 音声追加に失敗しました ({e})")


def test_video_creation():
    """テスト動画の生成確認"""
    test_video_path = "/tmp/test_sleep_video.mp4"
    create_test_video(test_video_path, duration_sec=30, fps=10)

    assert Path(test_video_path).exists()
    print(f"✓ テスト動画作成成功: {test_video_path}")


def test_video_metadata():
    """動画メタデータ取得テスト"""
    test_video_path = "/tmp/test_sleep_video.mp4"

    if not Path(test_video_path).exists():
        create_test_video(test_video_path, duration_sec=30, fps=10)

    metadata = video.get_video_metadata(test_video_path)

    assert metadata["duration"] > 0
    assert metadata["fps"] > 0
    assert metadata["width"] > 0
    assert metadata["height"] > 0

    print(f"✓ メタデータ取得成功: {metadata}")


def test_audio_extraction():
    """音声抽出テスト"""
    test_video_path = "/tmp/test_sleep_video.mp4"

    if not Path(test_video_path).exists():
        create_test_video(test_video_path, duration_sec=30, fps=10)

    audio_data, sr = audio.load_and_preprocess(test_video_path, target_sr=16000)

    assert len(audio_data) > 0
    assert sr == 16000

    print(f"✓ 音声抽出成功: {len(audio_data)} サンプル, SR={sr}")


def test_frame_extraction():
    """フレーム抽出テスト"""
    test_video_path = "/tmp/test_sleep_video.mp4"

    if not Path(test_video_path).exists():
        create_test_video(test_video_path, duration_sec=30, fps=10)

    frame = video.extract_frame_at_time(test_video_path, 5.0)

    assert frame is not None
    assert frame.shape[0] > 0
    assert frame.shape[1] > 0

    print(f"✓ フレーム抽出成功: {frame.shape}")


def test_analysis_pipeline():
    """解析パイプライン全体のテスト"""
    test_video_path = "/tmp/test_sleep_video.mp4"

    if not Path(test_video_path).exists():
        create_test_video(test_video_path, duration_sec=30, fps=10)

    print("\n" + "="*60)
    print("解析パイプライン実行テスト")
    print("="*60)

    cfg = analyzer.AnalysisConfig()
    results = analyzer.analyze(test_video_path, cfg)

    assert results.duration_sec > 0
    assert results.sr > 0
    assert len(results.waveform_downsampled["t"]) > 0
    assert len(results.waveform_downsampled["y"]) > 0
    assert "apnea_count" in results.summary

    print("\n" + "="*60)
    print("解析結果:")
    print(f"  録画時間: {results.duration_sec:.1f}秒")
    print(f"  無呼吸回数: {results.summary['apnea_count']}")
    print(f"  いびき回数: {results.summary['snore_count']}")
    print(f"  AHI推定: {results.summary['ahi_est']}")
    print("="*60)

    assert True
    print("✓ 解析パイプラインテスト成功")


def test_storage():
    """ストレージ機能テスト"""
    store = storage.Storage(base_dir="/tmp/test_sleep_storage")

    # ダミーデータで保存テスト
    job_id = "test-job-123"
    file_path = "/tmp/test_sleep_video.mp4"

    store.create_job(job_id, file_path, version="test-v1")

    # ジョブ取得
    job = store.get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id

    # 結果保存
    test_results = {
        "duration_sec": 30.0,
        "events": [],
        "summary": {
            "apnea_count": 0,
            "ahi_est": 0.0
        }
    }

    store.save_results(job_id, test_results)

    # 結果読み込み
    loaded = store.load_results(job_id)
    assert loaded is not None
    assert loaded["duration_sec"] == 30.0

    print("✓ ストレージテスト成功")


def test_full_e2e():
    """フルE2Eテスト (動画作成→解析→保存→読み込み)"""
    print("\n" + "="*60)
    print("フルE2Eテスト開始")
    print("="*60 + "\n")

    # 1. テスト動画作成
    test_video_path = "/tmp/test_sleep_e2e.mp4"
    print("[1/5] テスト動画作成中...")
    create_test_video(test_video_path, duration_sec=30, fps=10)
    print(f"  ✓ 作成完了: {test_video_path}")

    # 2. 解析実行
    print("\n[2/5] 解析実行中...")
    cfg = analyzer.AnalysisConfig()
    results = analyzer.analyze(test_video_path, cfg)
    print(f"  ✓ 解析完了")

    # 3. ストレージ保存
    print("\n[3/5] 結果保存中...")
    store = storage.Storage(base_dir="/tmp/test_sleep_e2e_storage")
    job_id = "e2e-test-job"
    store.create_job(job_id, test_video_path, cfg.version)
    store.save_results(job_id, results.to_dict())
    print(f"  ✓ 保存完了: ジョブID={job_id}")

    # 4. 結果読み込み
    print("\n[4/5] 結果読み込み中...")
    loaded_results = store.load_results(job_id)
    assert loaded_results is not None
    print(f"  ✓ 読み込み完了")

    # 5. フレーム取得
    print("\n[5/5] フレーム取得中...")
    frame = video.extract_frame_at_time(test_video_path, 5.0)
    assert frame is not None
    jpeg = video.encode_frame_to_jpeg(frame)
    assert len(jpeg) > 0
    print(f"  ✓ フレーム取得完了: {len(jpeg)} bytes")

    print("\n" + "="*60)
    print("フルE2Eテスト成功！")
    print("="*60 + "\n")


if __name__ == "__main__":
    # pytest実行
    pytest.main([__file__, "-v", "-s"])
