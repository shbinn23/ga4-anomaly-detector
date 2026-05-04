import json
import logging
from pathlib import Path
from .storage import BaseStorage
from ..core.config import settings
from ..domain.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

class JSONStorage(BaseStorage):
    """BaseStorage 인터페이스의 JSON 파일 구현체입니다."""

    def __init__(self):
        # settings.DATA_DIR를 사용하여 루트의 /data 폴더를 참조합니다.
        self.path = settings.DATA_DIR / settings.DB_FILE_NAME

    def save(self, key: str, data: dict):
        try:
            db = self.load_all()
            db[key] = data
            # 디렉토리가 없을 경우를 대비해 생성 시도
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
            logger.info(f"Successfully saved data for property: {key}")
        except Exception as e:
            logger.error(f"JSON 저장 실패: {str(e)}")
            raise InfrastructureError(f"Storage save failed: {str(e)}")

    def load_all(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 로드 실패: {str(e)}")
            return {}

    def save_batch(self, data_map: dict):
        """여러 프로퍼티의 분석 결과를 한 번의 I/O로 영속화합니다."""
        try:
            db = self.load_all()
            db.update(data_map)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
            logger.info(f"Successfully saved batch update for {len(data_map)} properties.")
        except Exception as e:
            logger.error(f"JSON 배치 저장 실패: {str(e)}")
            raise InfrastructureError(f"Batch storage failed: {str(e)}")

    def clear(self):
        try:
            if self.path.exists():
                self.path.unlink()
                logger.info("Database file cleared.")
        except Exception as e:
            raise InfrastructureError(f"Clear failed: {str(e)}")

    def save_all_channel_analysis(self, data: dict):
        """채널 분석 결과를 기존 데이터에 병합하여 영속화합니다."""
        path = self.path.parent / "channel_anomaly_db.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # 1. 기존 데이터 로드 (파일이 없으면 빈 딕셔너리로 초기화)
            db = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    db = json.load(f)

            # 2. 새로운 데이터 병합 (Update)
            db.update(data)

            # 3. 전체 데이터 다시 덮어쓰기 (이제 기존 데이터가 날아가지 않음)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=4)

            logger.info(f"Successfully updated channel analysis. Total properties in DB: {len(db)}")
        except Exception as e:
            logger.error(f"채널 분석 저장 실패: {str(e)}")
            raise InfrastructureError(f"Channel analysis storage failed: {str(e)}")