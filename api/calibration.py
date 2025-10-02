"""
キャリブレーション用API
ユーザーがマークした無呼吸区間からパラメータを学習
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List
import sys
from pathlib import Path
import numpy as np
import tempfile

sys.path.append(str(Path(__file__).parent.parent))

from services import audio_simple, video as video_module
from services.storage import Storage

router = APIRouter(prefix="/calibrate", tags=["calibration"])
storage = Storage(base_dir="./data")


class MarkerInput(BaseModel):
    """マーク入力"""
    start: float
    end: float


class CalculateRequest(BaseModel):
    """パラメータ計算リクエスト"""
    job_id: str
    markers: List[MarkerInput]


@router.post("/analyze")
async def analyze_for_calibration(file: UploadFile = File(...)):
    """
    キャリブレーション用の音声解析（動画・音声両対応）
    波形データと音声ファイルを返す
    """
    try:
        # ファイル保存
        file_data = await file.read()
        file_size = len(file_data)
        job_id, file_path = storage.save_upload(file_data, file.filename)

        print(f"\n[キャリブレーション] ジョブID: {job_id}")
        print(f"  ファイルサイズ: {file_size / 1024 / 1024:.1f}MB")

        # ファイル拡張子でタイプ判定
        file_ext = file.filename.lower().split('.')[-1]

        # 動画形式
        video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'm4v',
                           '3gp', 'mpg', 'mpeg', 'ogv']
        # 音声形式
        audio_extensions = ['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'opus',
                           'aiff', 'aif']

        if file_ext in video_extensions:
            # 動画処理パターン
            metadata = video_module.get_video_metadata(file_path)
            duration = metadata['duration']
            print(f"  動画ファイル: {file.filename}")
            print(f"  動画長: {duration:.1f}秒")
        elif file_ext in audio_extensions:
            # 音声処理パターン
            duration = audio_simple.get_audio_duration(file_path)
            print(f"  音声ファイル: {file.filename}")
            print(f"  音声長: {duration:.1f}秒")
        else:
            raise HTTPException(status_code=400, detail=f"非対応のファイル形式です: {file_ext}")

        # 音声処理
        cfg = audio_simple.SimpleAudioConfig()
        audio_data, sr = audio_simple.load_and_preprocess(file_path, cfg.audio_sr)
        print(f"  音声サンプル数: {len(audio_data):,}")

        # RMS計算
        times, rms = audio_simple.compute_rms_energy(audio_data, sr, cfg)
        print(f"  RMSフレーム数: {len(rms):,}")

        # ダウンサンプリングなし（全データ送信）
        down_t, down_y = times, rms

        # 音声ファイルを一時保存（再生用）
        audio_path = Path(storage.uploads_dir) / f"{job_id}_audio.wav"

        # FFmpegで音声抽出
        import subprocess
        cmd = [
            'ffmpeg', '-i', file_path,
            '-vn', '-acodec', 'libmp3lame', '-q:a', '4',
            '-y', str(audio_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # ジョブ作成
        storage.create_job(job_id, file_path, "calibration-v1")

        # RMSデータを保存
        result_data = {
            "job_id": job_id,
            "duration_sec": duration,
            "sr": sr,
            "waveform": {
                "t": down_t.tolist(),
                "y": down_y.tolist()
            },
            "rms_full": {
                "t": times.tolist(),
                "y": rms.tolist()
            }
        }

        storage.save_results(job_id, result_data)

        return result_data

    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio")
async def get_audio(job_id: str):
    """
    音声ファイルを取得
    """
    audio_path = Path(storage.uploads_dir) / f"{job_id}_audio.wav"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音声ファイルが見つかりません")

    return FileResponse(str(audio_path), media_type="audio/mpeg")


@router.post("/calculate")
async def calculate_parameters(request: CalculateRequest):
    """
    マークされた無呼吸区間からパラメータを計算
    """
    try:
        # 結果読み込み
        results = storage.load_results(request.job_id)
        if results is None:
            raise HTTPException(status_code=404, detail="解析結果が見つかりません")

        rms_full = results["rms_full"]
        times = np.array(rms_full["t"])
        rms = np.array(rms_full["y"])

        print(f"\n[パラメータ計算] マーク数: {len(request.markers)}")

        # 各マーク区間の特性を分析
        silence_values = []
        resume_peaks = []

        for marker in request.markers:
            start = marker.start
            end = marker.end

            # マーク区間内のRMS値を取得
            mask = (times >= start) & (times <= end)
            silence_rms = rms[mask]

            if len(silence_rms) > 0:
                # 無音区間の平均RMS
                avg_silence = np.mean(silence_rms)
                silence_values.append(avg_silence)

                # 無音終了後のピーク音（10フレーム = 約0.5秒）
                end_idx = np.where(times >= end)[0]
                if len(end_idx) > 0:
                    start_idx = end_idx[0]
                    check_frames = min(10, len(rms) - start_idx)
                    if check_frames > 0:
                        resume_peak = np.max(rms[start_idx:start_idx+check_frames])
                        resume_peaks.append(resume_peak)

                print(f"  マーク {start:.1f}s-{end:.1f}s: 無音RMS={avg_silence:.6f}")

        if len(silence_values) == 0:
            raise HTTPException(status_code=400, detail="有効なマークがありません")

        # パラメータ計算
        # 無音閾値: マークした区間の平均RMSの平均値
        silence_threshold = float(np.mean(silence_values))

        # 呼吸再開倍率: 無音閾値に対する再開ピークの比率の平均
        if len(resume_peaks) > 0:
            ratios = [peak / silence_threshold for peak in resume_peaks]
            resume_multiplier = float(np.mean(ratios))
        else:
            resume_multiplier = 2.0  # デフォルト

        print(f"  計算結果:")
        print(f"    無音閾値: {silence_threshold:.6f}")
        print(f"    呼吸再開倍率: {resume_multiplier:.2f}x")

        # パラメータを保存
        params = {
            "silence_threshold": silence_threshold,
            "resume_multiplier": resume_multiplier,
            "marker_count": len(request.markers),
            "silence_values": [float(v) for v in silence_values],
            "resume_peaks": [float(p) for p in resume_peaks]
        }

        # 結果に追加保存
        results["calibration_params"] = params
        storage.save_results(request.job_id, results)

        return params

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(limit: int = 20):
    """
    アップロード済みジョブ一覧を取得
    """
    try:
        jobs = storage.list_jobs(limit=limit)
        return {"jobs": jobs}
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/job/{job_id}/name")
async def update_job_name(job_id: str, name: str):
    """
    ジョブ名を更新
    """
    try:
        success = storage.update_job_name(job_id, name)
        if not success:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        return {"success": True, "job_id": job_id, "name": name}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load")
async def load_existing_job(job_id: str):
    """
    既存ジョブのデータを再読み込み
    """
    try:
        # ジョブ情報取得
        job = storage.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")

        # 結果データ読み込み
        results = storage.load_results(job_id)
        if results is None:
            raise HTTPException(status_code=404, detail="解析結果が見つかりません")

        # ジョブ情報を結果に追加
        results["recording_start_datetime"] = job.get("recording_start_datetime")
        results["time_display_mode"] = job.get("time_display_mode", "relative")

        print(f"\n[ジョブ再読み込み] ID: {job_id}")

        return results

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    ジョブとその関連ファイルを削除
    """
    try:
        success = storage.delete_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")

        print(f"\n[ジョブ削除] ID: {job_id}")
        return {"success": True, "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-candidates")
async def extract_candidates(job_id: str, top_n: int = 50):
    """
    RMSエネルギーのピーク上位N件を候補として抽出

    Args:
        job_id: ジョブID
        top_n: 抽出する候補数（デフォルト50）

    Returns:
        候補ポイントのリスト
    """
    try:
        # 結果読み込み
        results = storage.load_results(job_id)
        if results is None:
            raise HTTPException(status_code=404, detail="解析結果が見つかりません")

        rms_full = results["rms_full"]
        times = np.array(rms_full["t"])
        rms = np.array(rms_full["y"])

        print(f"\n[候補抽出] ジョブID: {job_id}")
        print(f"  RMSフレーム数: {len(rms):,}")

        # ピーク検出（局所最大値を探す）
        from scipy.signal import find_peaks

        # ピーク検出（最小距離=20フレーム=約1秒）
        peaks, properties = find_peaks(rms, distance=20, prominence=0.0001)

        # ピーク値で降順ソート
        peak_values = rms[peaks]
        sorted_indices = np.argsort(peak_values)[::-1]

        # 上位N件を取得
        top_peaks = peaks[sorted_indices[:top_n]]
        top_values = peak_values[sorted_indices[:top_n]]

        # 候補リスト作成（RMSエネルギーが高い順）
        candidates = []
        for i, (peak_idx, peak_value) in enumerate(zip(top_peaks, top_values)):
            peak_time = times[peak_idx]

            # 無呼吸区間の推定（ピークの10秒前〜ピーク直前）
            apnea_start = max(0, peak_time - 10.0)
            apnea_end = peak_time

            candidates.append({
                "id": i,
                "peak_time": float(peak_time),
                "peak_rms": float(peak_value),
                "apnea_start": float(apnea_start),
                "apnea_end": float(apnea_end),
                "status": "pending"  # pending, apnea, skip
            })

        print(f"  抽出した候補数: {len(candidates)}")
        print(f"  RMS範囲: {top_values.min():.6f} 〜 {top_values.max():.6f}")

        return {
            "job_id": job_id,
            "candidate_count": len(candidates),
            "candidates": candidates
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-judgment")
async def save_judgment(job_id: str, candidate_id: int, status: str):
    """
    候補の判定結果を保存

    Args:
        job_id: ジョブID
        candidate_id: 候補ID
        status: 判定結果 (pending/apnea/skip)

    Returns:
        保存成功レスポンス
    """
    try:
        storage.save_candidate_judgment(job_id, candidate_id, status)
        print(f"[判定保存] ジョブID: {job_id}, 候補ID: {candidate_id}, 判定: {status}")
        return {"success": True, "job_id": job_id, "candidate_id": candidate_id, "status": status}

    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/judgments")
async def get_judgments(job_id: str):
    """
    ジョブの全候補判定結果を取得

    Args:
        job_id: ジョブID

    Returns:
        候補IDをキーとした判定結果の辞書
    """
    try:
        judgments = storage.get_candidate_judgments(job_id)
        print(f"[判定取得] ジョブID: {job_id}, 判定数: {len(judgments)}")
        return {"job_id": job_id, "judgments": judgments}

    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/job/{job_id}/recording-time")
async def update_recording_time(job_id: str, recording_start_datetime: str):
    """
    撮影開始日時を設定

    Args:
        job_id: ジョブID
        recording_start_datetime: 撮影開始日時（ISO8601形式: YYYY-MM-DDTHH:MM:SS）

    Returns:
        成功レスポンス
    """
    try:
        success = storage.update_recording_datetime(job_id, recording_start_datetime)
        if not success:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")

        print(f"[撮影日時設定] ジョブID: {job_id}, 日時: {recording_start_datetime}")
        return {"success": True, "job_id": job_id, "recording_start_datetime": recording_start_datetime}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/job/{job_id}/display-mode")
async def update_display_mode(job_id: str, mode: str):
    """
    時刻表示モードを切り替え

    Args:
        job_id: ジョブID
        mode: 表示モード（'relative' or 'absolute'）

    Returns:
        成功レスポンス
    """
    try:
        success = storage.update_time_display_mode(job_id, mode)
        if not success:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません、または無効なモードです")

        print(f"[表示モード変更] ジョブID: {job_id}, モード: {mode}")
        return {"success": True, "job_id": job_id, "mode": mode}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class CandidateJudgmentsRequest(BaseModel):
    """候補判定結果"""
    candidates: List[dict]


@router.post("/judgment-summary")
async def get_judgment_summary(request: CandidateJudgmentsRequest):
    """
    判定結果のサマリを計算

    Args:
        candidates: 候補リスト（status付き）

    Returns:
        統計情報
    """
    try:
        candidates = request.candidates
        apnea_candidates = [c for c in candidates if c.get('status') == 'apnea']
        skip_candidates = [c for c in candidates if c.get('status') == 'skip']
        pending_candidates = [c for c in candidates if c.get('status') == 'pending']

        apnea_count = len(apnea_candidates)
        skip_count = len(skip_candidates)
        pending_count = len(pending_candidates)
        total = len(candidates)

        summary = {
            "total": total,
            "apnea_count": apnea_count,
            "skip_count": skip_count,
            "pending_count": pending_count,
            "apnea_percentage": (apnea_count / total * 100) if total > 0 else 0,
            "skip_percentage": (skip_count / total * 100) if total > 0 else 0
        }

        # 無呼吸のRMS統計
        if apnea_count > 0:
            apnea_rms_values = [c['peak_rms'] for c in apnea_candidates]
            mean_rms = float(np.mean(apnea_rms_values))
            std_rms = float(np.std(apnea_rms_values))
            min_rms = float(np.min(apnea_rms_values))
            max_rms = float(np.max(apnea_rms_values))

            summary["apnea_statistics"] = {
                "mean_rms": mean_rms,
                "std_rms": std_rms,
                "min_rms": min_rms,
                "max_rms": max_rms,
                "range_2sigma": {
                    "lower": max(0, mean_rms - 2 * std_rms),
                    "upper": mean_rms + 2 * std_rms
                },
                "range_1sigma": {
                    "lower": max(0, mean_rms - std_rms),
                    "upper": mean_rms + std_rms
                }
            }

            print(f"[判定サマリ] 無呼吸: {apnea_count}件, 平均RMS: {mean_rms:.6f}, 標準偏差: {std_rms:.6f}")
        else:
            summary["apnea_statistics"] = None
            print(f"[判定サマリ] 無呼吸判定なし")

        return summary

    except Exception as e:
        print(f"[エラー] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class AdditionalCandidatesRequest(BaseModel):
    """追加候補抽出リクエスト"""
    job_id: str
    reference_candidate_ids: List[int]
    sigma_range: float = 2.0
    max_candidates: int = 30


class AHICalculationRequest(BaseModel):
    """AHI計算リクエスト"""
    job_id: str
    apnea_events: List[dict]  # {"id", "peak_time", "apnea_start", "apnea_end"}


@router.post("/extract-additional-candidates")
async def extract_additional_candidates(request: AdditionalCandidatesRequest):
    """
    統計ベースで追加候補を抽出

    Args:
        job_id: ジョブID
        reference_candidate_ids: 無呼吸と判定された候補のID
        sigma_range: 標準偏差の範囲（デフォルト2.0）
        max_candidates: 最大抽出数

    Returns:
        追加候補リスト
    """
    try:
        # 結果読み込み
        results = storage.load_results(request.job_id)
        if results is None:
            raise HTTPException(status_code=404, detail="解析結果が見つかりません")

        rms_full = results["rms_full"]
        times = np.array(rms_full["t"])
        rms = np.array(rms_full["y"])

        # 既存候補を取得（最初の抽出時のもの）
        existing_response = await extract_candidates(request.job_id, top_n=50)
        existing_candidates = existing_response["candidates"]
        existing_peak_times = set(c["peak_time"] for c in existing_candidates)

        # 参照候補（無呼吸判定されたもの）のRMS値を取得
        reference_rms_values = []
        for cand in existing_candidates:
            if cand["id"] in request.reference_candidate_ids:
                reference_rms_values.append(cand["peak_rms"])

        if len(reference_rms_values) == 0:
            raise HTTPException(status_code=400, detail="無呼吸判定された候補がありません")

        # 統計計算
        mean_rms = float(np.mean(reference_rms_values))
        std_rms = float(np.std(reference_rms_values))
        lower_bound = max(0, mean_rms - request.sigma_range * std_rms)
        upper_bound = mean_rms + request.sigma_range * std_rms

        print(f"\n[追加候補抽出] ジョブID: {request.job_id}")
        print(f"  参照候補数: {len(reference_rms_values)}")
        print(f"  平均RMS: {mean_rms:.6f}, 標準偏差: {std_rms:.6f}")
        print(f"  抽出範囲: {lower_bound:.6f} 〜 {upper_bound:.6f}")

        # ピーク検出
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(rms, distance=20, prominence=0.0001)

        # 範囲内のピークを抽出
        additional_candidates = []
        for peak_idx in peaks:
            peak_time = times[peak_idx]
            peak_rms = rms[peak_idx]

            # 既存候補に含まれていないかチェック
            if peak_time in existing_peak_times:
                continue

            # RMS範囲チェック
            if lower_bound <= peak_rms <= upper_bound:
                # 信頼度スコア（中心からの距離が近いほど高い）
                distance_from_mean = abs(peak_rms - mean_rms)
                confidence = 1.0 - (distance_from_mean / (request.sigma_range * std_rms))

                apnea_start = max(0, peak_time - 10.0)
                apnea_end = peak_time

                additional_candidates.append({
                    "peak_time": float(peak_time),
                    "peak_rms": float(peak_rms),
                    "confidence": float(confidence),
                    "apnea_start": float(apnea_start),
                    "apnea_end": float(apnea_end)
                })

        # 信頼度順にソート
        additional_candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # 最大数まで取得
        additional_candidates = additional_candidates[:request.max_candidates]

        # IDを割り当て（既存候補の続きから）
        start_id = len(existing_candidates)
        for i, cand in enumerate(additional_candidates):
            cand["id"] = start_id + i
            cand["status"] = "pending"

        print(f"  抽出した追加候補数: {len(additional_candidates)}")

        return {
            "job_id": request.job_id,
            "statistics": {
                "mean_rms": mean_rms,
                "std_rms": std_rms,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "reference_count": len(reference_rms_values)
            },
            "candidate_count": len(additional_candidates),
            "candidates": additional_candidates
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-ahi")
async def calculate_ahi(request: AHICalculationRequest):
    """
    AHI（Apnea-Hypopnea Index）を計算
    スライディングウィンドウ方式で1時間あたりの無呼吸イベント数を算出

    Args:
        job_id: ジョブID
        apnea_events: 無呼吸イベントのリスト

    Returns:
        AHI推移データと最大AHI情報
    """
    try:
        # 結果読み込み
        results = storage.load_results(request.job_id)
        if results is None:
            raise HTTPException(status_code=404, detail="解析結果が見つかりません")

        total_duration = results.get("duration_sec", 0)

        if len(request.apnea_events) == 0:
            return {
                "job_id": request.job_id,
                "total_duration": total_duration,
                "total_events": 0,
                "overall_ahi": 0.0,
                "severity": "正常",
                "max_ahi": 0.0,
                "worst_period": None,
                "timeline": []
            }

        # イベント時刻を配列化
        event_times = np.array([e["peak_time"] for e in request.apnea_events])
        event_times = np.sort(event_times)

        print(f"\n[AHI計算] ジョブID: {request.job_id}")
        print(f"  総録音時間: {total_duration/3600:.2f}時間")
        print(f"  無呼吸イベント数: {len(event_times)}件")

        # スライディングウィンドウ設定
        window_size = 3600  # 1時間（秒）
        step_size = 300     # 5分（秒）

        # AHI推移を計算
        ahi_timeline = []
        max_ahi = 0.0
        worst_period_start = 0

        # 最初の1時間未満は計算しない（データ不足）
        if total_duration < window_size:
            # 総時間が1時間未満の場合は全体のAHIのみ計算
            overall_ahi = len(event_times) / (total_duration / 3600)
            print(f"  全体AHI: {overall_ahi:.1f} (録音時間が1時間未満)")
        else:
            # スライディングウィンドウで計算
            current_time = 0
            while current_time + window_size <= total_duration:
                window_start = current_time
                window_end = current_time + window_size

                # この窓内のイベント数をカウント
                events_in_window = np.sum((event_times >= window_start) & (event_times < window_end))
                ahi = float(events_in_window)  # 1時間窓なのでそのままAHI

                ahi_timeline.append({
                    "time": float(window_start),
                    "ahi": ahi,
                    "window_start": float(window_start),
                    "window_end": float(window_end)
                })

                # 最大AHI更新
                if ahi > max_ahi:
                    max_ahi = ahi
                    worst_period_start = window_start

                current_time += step_size

            # 全体のAHI（総イベント数 / 総時間）
            overall_ahi = len(event_times) / (total_duration / 3600)

            print(f"  全体AHI: {overall_ahi:.1f}")
            print(f"  最大AHI: {max_ahi:.1f} (時刻: {worst_period_start:.0f}秒)")

        # 重症度判定
        if overall_ahi < 5:
            severity = "正常"
            severity_level = 0
        elif overall_ahi < 15:
            severity = "軽度"
            severity_level = 1
        elif overall_ahi < 30:
            severity = "中等度"
            severity_level = 2
        else:
            severity = "重度"
            severity_level = 3

        # 最悪期間の情報
        worst_period = None
        if max_ahi > 0 and total_duration >= window_size:
            worst_period = {
                "start_time": float(worst_period_start),
                "end_time": float(worst_period_start + window_size),
                "ahi": float(max_ahi)
            }

        result = {
            "job_id": request.job_id,
            "total_duration": float(total_duration),
            "total_events": len(event_times),
            "overall_ahi": float(overall_ahi),
            "severity": severity,
            "severity_level": severity_level,
            "max_ahi": float(max_ahi),
            "worst_period": worst_period,
            "timeline": ahi_timeline
        }

        print(f"  重症度: {severity}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[エラー] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
