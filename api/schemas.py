"""
API スキーマ定義
"""
from pydantic import BaseModel
from typing import List, Dict, Optional


class EventSchema(BaseModel):
    """イベントスキーマ"""
    type: str
    start: float
    end: float
    confidence: Optional[float] = None
    level: Optional[float] = None


class WaveformSchema(BaseModel):
    """波形スキーマ"""
    t: List[float]
    y: List[float]


class SummarySchema(BaseModel):
    """サマリスキーマ"""
    apnea_count: int
    apnea_avg_duration: float
    apnea_max_duration: float
    apnea_total_duration: float
    recording_hours: float
    ahi_est: float
    snore_count: int
    snore_total_duration: float
    snore_index: float


class AnalyzeResponse(BaseModel):
    """解析レスポンス"""
    job_id: str
    status: str
    results: Optional[Dict] = None


class ResultsResponse(BaseModel):
    """結果レスポンス"""
    duration_sec: float
    sr: int
    waveform_downsampled: WaveformSchema
    events: List[EventSchema]
    summary: SummarySchema
    version: str


class JobResponse(BaseModel):
    """ジョブレスポンス"""
    job_id: str
    file_path: str
    created_at: str
    version: str
    status: str
