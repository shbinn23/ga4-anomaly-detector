import pytest
import pandas as pd
from app.ml.prophet_detector import ProphetDetector

def test_prophet_prediction_logic():
    # 1. 테스트용 더미 데이터 생성 (30일치)
    dates = pd.date_range(start="2026-01-01", periods=30)
    data = {"ds": dates, "y": [100 + i for i in range(30)]}
    df = pd.DataFrame(data)

    detector = ProphetDetector()

    # 2. 학습 및 예측 수행
    forecast = detector.train_and_predict(df)

    # 3. 검증
    assert not forecast.empty
    assert "yhat" in forecast.columns
    assert "yhat_lower" in forecast.columns
    assert "yhat_upper" in forecast.columns
    # 데이터 포인트 개수가 일치하는지 확인
    assert len(forecast) == len(df)

def test_anomaly_check_logic():
    detector = ProphetDetector()
    # 상한선 돌파 케이스
    assert detector.check_anomaly(150, 80, 120) is True
    # 하한선 미달 케이스
    assert detector.check_anomaly(50, 80, 120) is True
    # 정상 범위 케이스
    assert detector.check_anomaly(100, 80, 120) is False