import logging
import sys
from .config import settings

def setup_logging():
    # 기본 로그 포맷 정의
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            # 향후 파일 로그가 필요하면 여기에 추가
        ]
    )

    # Prophet의 수다스러운 로그 제어
    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)

logger = logging.getLogger(settings.PROJECT_NAME)