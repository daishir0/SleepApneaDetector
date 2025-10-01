"""
ストレージモジュール
ファイル保存、データベース操作、フレーム抽出などを管理
"""
import os
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
import shutil


class Storage:
    """ストレージマネージャー"""

    def __init__(self, base_dir: str = "./data"):
        self.base_dir = Path(base_dir)
        self.uploads_dir = self.base_dir / "uploads"
        self.results_dir = self.base_dir / "results"
        self.db_path = self.base_dir / "sleep_analysis.db"

        # ディレクトリ作成
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # データベース初期化
        self._init_database()

    def _init_database(self):
        """データベースの初期化"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # ジョブテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                created_at TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                recording_start_datetime TEXT,
                time_display_mode TEXT DEFAULT 'relative'
            )
        """)

        # 既存テーブルへのカラム追加（マイグレーション）
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN recording_start_datetime TEXT")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合

        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN time_display_mode TEXT DEFAULT 'relative'")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合

        # イベントテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                type TEXT NOT NULL,
                start REAL NOT NULL,
                end REAL NOT NULL,
                confidence REAL,
                level REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        # サマリテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary (
                job_id TEXT PRIMARY KEY,
                apnea_count INTEGER,
                avg_dur REAL,
                max_dur REAL,
                ahi_est REAL,
                snore_index REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        # 候補判定テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_judgments (
                job_id TEXT NOT NULL,
                candidate_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (job_id, candidate_id),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        conn.commit()
        conn.close()

    def save_upload(self, file_data: bytes, original_filename: str) -> tuple[str, str]:
        """
        アップロードファイルを保存

        Args:
            file_data: ファイルデータ
            original_filename: 元のファイル名

        Returns:
            (job_id, 保存されたファイルパス)
        """
        job_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix
        save_path = self.uploads_dir / f"{job_id}{ext}"

        with open(save_path, "wb") as f:
            f.write(file_data)

        return job_id, str(save_path)

    def create_job(self, job_id: str, file_path: str, version: str = "rule-v0.3.1", name: str = None, file_size: int = None):
        """
        ジョブを作成

        Args:
            job_id: ジョブID
            file_path: 動画ファイルパス
            version: 解析バージョン
            name: ジョブ名（任意）
            file_size: ファイルサイズ（バイト）
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO jobs (job_id, name, file_path, file_size, created_at, version, status)
            VALUES (?, ?, ?, ?, ?, ?, 'processing')
        """, (job_id, name, file_path, file_size, datetime.now().isoformat(), version))

        conn.commit()
        conn.close()

    def save_results(self, job_id: str, results: Dict):
        """
        解析結果を保存

        Args:
            job_id: ジョブID
            results: 解析結果辞書
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # イベント保存
        for event in results.get("events", []):
            cursor.execute("""
                INSERT INTO events (job_id, type, start, end, confidence, level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                event["type"],
                event["start"],
                event["end"],
                event.get("confidence"),
                event.get("level")
            ))

        # サマリ保存
        summary = results.get("summary", {})
        cursor.execute("""
            INSERT OR REPLACE INTO summary (job_id, apnea_count, avg_dur, max_dur, ahi_est, snore_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            summary.get("apnea_count", 0),
            summary.get("apnea_avg_duration", 0.0),
            summary.get("apnea_max_duration", 0.0),
            summary.get("ahi_est", 0.0),
            summary.get("snore_index", 0.0)
        ))

        # JSON結果ファイル保存
        result_path = self.results_dir / f"{job_id}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # ジョブステータス更新
        cursor.execute("""
            UPDATE jobs SET status = 'completed' WHERE job_id = ?
        """, (job_id,))

        conn.commit()
        conn.close()

    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        ジョブ情報を取得

        Args:
            job_id: ジョブID

        Returns:
            ジョブ情報辞書、存在しない場合はNone
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, file_path, created_at, version, status, recording_start_datetime, time_display_mode
            FROM jobs WHERE job_id = ?
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "job_id": row[0],
                "file_path": row[1],
                "created_at": row[2],
                "version": row[3],
                "status": row[4],
                "recording_start_datetime": row[5],
                "time_display_mode": row[6] or 'relative'
            }
        return None

    def load_results(self, job_id: str) -> Optional[Dict]:
        """
        解析結果をロード

        Args:
            job_id: ジョブID

        Returns:
            解析結果辞書、存在しない場合はNone
        """
        result_path = self.results_dir / f"{job_id}.json"

        if result_path.exists():
            with open(result_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_video_path(self, job_id: str) -> Optional[str]:
        """
        ジョブIDから動画ファイルパスを取得

        Args:
            job_id: ジョブID

        Returns:
            動画ファイルパス、存在しない場合はNone
        """
        job = self.get_job(job_id)
        if job:
            return job["file_path"]
        return None

    def list_jobs(self, limit: int = 10) -> List[Dict]:
        """
        ジョブ一覧を取得

        Args:
            limit: 最大件数

        Returns:
            ジョブ情報のリスト
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, name, file_path, file_size, created_at, version, status
            FROM jobs
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "job_id": row[0],
                "name": row[1],
                "file_path": row[2],
                "file_size": row[3],
                "created_at": row[4],
                "version": row[5],
                "status": row[6]
            }
            for row in rows
        ]

    def update_job_name(self, job_id: str, name: str) -> bool:
        """
        ジョブ名を更新

        Args:
            job_id: ジョブID
            name: 新しい名前

        Returns:
            成功したらTrue
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE jobs SET name = ? WHERE job_id = ?
        """, (name, job_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def delete_job(self, job_id: str) -> bool:
        """
        ジョブと関連ファイルを削除

        Args:
            job_id: ジョブID

        Returns:
            成功したらTrue
        """
        # ジョブ情報取得
        job = self.get_job(job_id)
        if not job:
            return False

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # データベースから削除
            cursor.execute("DELETE FROM events WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM summary WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()

            # ファイル削除
            # 動画ファイル
            video_path = Path(job["file_path"])
            if video_path.exists():
                video_path.unlink()

            # 音声ファイル
            audio_path = self.uploads_dir / f"{job_id}_audio.wav"
            if audio_path.exists():
                audio_path.unlink()

            # 結果JSONファイル
            result_path = self.results_dir / f"{job_id}.json"
            if result_path.exists():
                result_path.unlink()

            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def save_candidate_judgment(self, job_id: str, candidate_id: int, status: str):
        """
        候補の判定結果を保存

        Args:
            job_id: ジョブID
            candidate_id: 候補ID
            status: 判定結果 (pending/apnea/skip)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO candidate_judgments (job_id, candidate_id, status, updated_at)
            VALUES (?, ?, ?, ?)
        """, (job_id, candidate_id, status, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_candidate_judgments(self, job_id: str) -> Dict[int, str]:
        """
        ジョブの全候補判定結果を取得

        Args:
            job_id: ジョブID

        Returns:
            候補IDをキーとした判定結果の辞書
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT candidate_id, status
            FROM candidate_judgments
            WHERE job_id = ?
        """, (job_id,))

        rows = cursor.fetchall()
        conn.close()

        return {row[0]: row[1] for row in rows}

    def update_recording_datetime(self, job_id: str, recording_start_datetime: str) -> bool:
        """
        撮影開始日時を更新

        Args:
            job_id: ジョブID
            recording_start_datetime: 撮影開始日時（ISO8601形式）

        Returns:
            成功したらTrue
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE jobs SET recording_start_datetime = ? WHERE job_id = ?
        """, (recording_start_datetime, job_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def update_time_display_mode(self, job_id: str, mode: str) -> bool:
        """
        時刻表示モードを更新

        Args:
            job_id: ジョブID
            mode: 表示モード（'relative' or 'absolute'）

        Returns:
            成功したらTrue
        """
        if mode not in ['relative', 'absolute']:
            return False

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE jobs SET time_display_mode = ? WHERE job_id = ?
        """, (mode, job_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0
