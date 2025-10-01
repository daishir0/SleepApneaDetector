"""
FastAPI メインアプリケーション
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys

# モジュールパスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services.analyzer import analyze, AnalysisConfig
from services.storage import Storage
from services import video as video_module
from api.schemas import AnalyzeResponse, ResultsResponse, JobResponse
from api.calibration import router as calibration_router

app = FastAPI(title="Sleep Apnea Detection API", version="0.3.1")

# キャリブレーションルーター追加
app.include_router(calibration_router)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ストレージ初期化
storage = Storage(base_dir="./data")

# 静的ファイル配信
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/")
async def root():
    """ルート"""
    # index.htmlがあれば返す
    index_path = web_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Sleep Apnea Detection API", "version": "0.3.1"}


@app.get("/calibration")
async def calibration_page():
    """キャリブレーション画面"""
    calibration_path = web_dir / "calibration.html"
    if calibration_path.exists():
        return FileResponse(str(calibration_path))
    raise HTTPException(status_code=404, detail="Calibration page not found")


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(file: UploadFile = File(...)):
    """
    動画を解析

    Args:
        file: アップロードされた動画ファイル

    Returns:
        解析結果
    """
    try:
        # ファイル保存
        file_data = await file.read()
        job_id, file_path = storage.save_upload(file_data, file.filename)

        # ジョブ作成
        cfg = AnalysisConfig()
        storage.create_job(job_id, file_path, cfg.version)

        # 解析実行
        print(f"\n{'='*60}")
        print(f"[ジョブ開始] ID: {job_id}")
        print(f"[ファイル] {file.filename}")
        print(f"{'='*60}\n")

        results = analyze(file_path, cfg)

        # 結果保存
        storage.save_results(job_id, results.to_dict())

        print(f"\n{'='*60}")
        print(f"[ジョブ完了] ID: {job_id}")
        print(f"{'='*60}\n")

        return AnalyzeResponse(
            job_id=job_id,
            status="completed",
            results=results.to_dict()
        )

    except Exception as e:
        print(f"[エラー] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results")
async def get_results(job_id: str):
    """
    解析結果を取得

    Args:
        job_id: ジョブID

    Returns:
        解析結果
    """
    results = storage.load_results(job_id)

    if results is None:
        raise HTTPException(status_code=404, detail="Results not found")

    return results


@app.get("/frame")
async def get_frame(job_id: str, t: float):
    """
    指定時刻のフレームを取得

    Args:
        job_id: ジョブID
        t: 時刻 (秒)

    Returns:
        JPEG画像
    """
    video_path = storage.get_video_path(job_id)

    if video_path is None:
        raise HTTPException(status_code=404, detail="Job not found")

    frame = video_module.extract_frame_at_time(video_path, t)

    if frame is None:
        raise HTTPException(status_code=404, detail="Frame not found")

    # JPEGエンコード
    jpeg_bytes = video_module.encode_frame_to_jpeg(frame, quality=85)

    return Response(content=jpeg_bytes, media_type="image/jpeg")


@app.get("/download")
async def download_results(job_id: str, fmt: str = "json"):
    """
    解析結果をダウンロード

    Args:
        job_id: ジョブID
        fmt: フォーマット (json or csv)

    Returns:
        ファイル
    """
    results = storage.load_results(job_id)

    if results is None:
        raise HTTPException(status_code=404, detail="Results not found")

    if fmt == "json":
        import json
        content = json.dumps(results, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"{job_id}_results.json"

    elif fmt == "csv":
        # CSVフォーマット (簡易版)
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow(["指標", "値"])

        # サマリ
        summary = results.get("summary", {})
        for key, value in summary.items():
            if key != "説明":
                writer.writerow([key, value])

        # イベント
        writer.writerow([])
        writer.writerow(["イベント種別", "開始時刻", "終了時刻", "信頼度/レベル"])

        for event in results.get("events", []):
            writer.writerow([
                event["type"],
                event["start"],
                event["end"],
                event.get("confidence", event.get("level", ""))
            ])

        content = output.getvalue()
        media_type = "text/csv"
        filename = f"{job_id}_results.csv"

    else:
        raise HTTPException(status_code=400, detail="Invalid format")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/jobs")
async def list_jobs(limit: int = 10):
    """
    ジョブ一覧を取得

    Args:
        limit: 最大件数

    Returns:
        ジョブリスト
    """
    jobs = storage.list_jobs(limit=limit)
    return {"jobs": jobs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
