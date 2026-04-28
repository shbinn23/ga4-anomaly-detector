from fastapi import status

class AppBaseException(Exception):
    """모든 애플리케이션 예외의 베이스"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class DetectionFailedError(AppBaseException):
    """분석 엔진(Prophet 등) 실행 실패 시 발생"""
    def __init__(self, message: str = "Anomaly detection engine failed"):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class InfrastructureError(AppBaseException):
    """파일 저장소나 외부 리소스 접근 실패 시 발생"""
    def __init__(self, message: str = "Data storage error occurred"):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)