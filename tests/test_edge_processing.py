import pytest
from src.drone.edge_processing import EdgeProcessor

def test_process_without_temperature_field():
    proc = EdgeProcessor(window_size=3, sigma_threshold=2.0)
    payload = {"sensor_id": "S1"}
    result = proc.process(payload.copy())
    # Missing temperature should leave payload unmodified (no 'average' key)
    assert "average" not in result

def test_process_computes_average_and_std_dev():
    proc = EdgeProcessor(window_size=3, sigma_threshold=2.0)
    data = [10, 20, 30]
    expected_avgs = [10, 15, 20]
    for i, temp in enumerate(data):
        payload = {"sensor_id": "S1", "timestamp": 0, "temperature": temp}
        result = proc.process(payload.copy())
        assert pytest.approx(result["average"], abs=0.01) == expected_avgs[i]
        if i == 0:
            assert result["std_dev"] == 0.0
        else:
            assert result["std_dev"] > 0.0
        assert "anomaly_flag" in result
        assert "processed_timestamp" in result

def test_anomaly_detection_triggers_flag():
    proc = EdgeProcessor(window_size=5, sigma_threshold=0.1)
    # Fill window with a constant value
    for _ in range(5):
        proc.process({"sensor_id": "S1", "timestamp": 0, "temperature": 10})
    # Now send an outlier
    outlier = {"sensor_id": "S1", "timestamp": 1, "temperature": 100}
    result = proc.process(outlier.copy())
    assert result["anomaly_flag"] is True