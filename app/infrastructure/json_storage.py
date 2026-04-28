import json
import logging
from pathlib import Path
from .storage import BaseStorage
from ..core.config import settings
from ..domain.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

class JSONStorage(BaseStorage):
    """BaseStorage 인터페이스의 JSON 파일 구현체입니다. [cite: 2026-02-26]"""

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

    def clear(self):
        try:
            if self.path.exists():
                self.path.unlink()
                logger.info("Database file cleared.")
        except Exception as e:
            raise InfrastructureError(f"Clear failed: {str(e)}")