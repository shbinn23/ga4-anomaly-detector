from abc import ABC, abstractmethod

class BaseStorage(ABC):
    """
    모든 데이터 저장소 구현체가 준수해야 하는 추상 인터페이스입니다.
    비즈니스 로직이 특정 저장 기술(JSON, SQL 등)에 종속되지 않도록 보호합니다. [cite: 2026-02-26]
    """

    @abstractmethod
    def save(self, key: str, data: dict):
        """데이터를 저장소에 저장합니다."""
        pass

    @abstractmethod
    def load_all(self) -> dict:
        """저장소의 모든 데이터를 로드합니다."""
        pass

    @abstractmethod
    def clear(self):
        """저장소의 데이터를 초기화(삭제)합니다."""
        pass