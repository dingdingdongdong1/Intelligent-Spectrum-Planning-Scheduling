from __future__ import annotations

from backend.app.services.channels import candidate_channels_for_station, generate_channels
from backend.app.services.chat import parse_chat_instruction
from backend.app.services.interference import estimate_interference_risk
from backend.app.services.optimizer import solve_frequency_assignment
from backend.app.services.validation import validate_inputs
from backend.app.services.visualization import build_visualization_data


def _rules() -> list[dict]:
    return [
        {
            "id": 1,
            "band_group": "UHF-A",
            "service_type": "专网语音",
            "region": "default",
            "start_mhz": 410.0,
            "end_mhz": 410.2,
            "channel_step_khz": 25.0,
            "max_bandwidth_khz": 25.0,
            "max_power_w": 50.0,
            "guard_band_khz": 0.0,
            "min_spacing_khz": 50.0,
            "forbidden_frequency_mhz": 410.05,
            "protection_distance_km": 5.0,
        }
    ]


def _stations() -> list[dict]:
    return [
        {
            "station_id": "S001",
            "name": "A",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "service_type": "专网语音",
            "bandwidth_khz": 25.0,
            "tx_power_w": 20.0,
            "antenna_height_m": 30.0,
            "antenna_gain_dbi": 6.0,
            "available_band_group": "UHF-A",
            "protection_distance_km": 5.0,
            "priority": 5,
            "existing_frequency_mhz": None,
            "forbidden_frequencies_mhz": "",
        },
        {
            "station_id": "S002",
            "name": "B",
            "latitude": 31.231,
            "longitude": 121.474,
            "service_type": "专网语音",
            "bandwidth_khz": 25.0,
            "tx_power_w": 20.0,
            "antenna_height_m": 28.0,
            "antenna_gain_dbi": 6.0,
            "available_band_group": "UHF-A",
            "protection_distance_km": 5.0,
            "priority": 4,
            "existing_frequency_mhz": None,
            "forbidden_frequencies_mhz": "410.0",
        },
    ]


def test_generate_channels_excludes_rule_forbidden_frequency() -> None:
    channels = generate_channels(_rules())
    freqs = {round(channel.frequency_mhz, 3) for channel in channels}
    assert 410.05 not in freqs
    assert 410.0 in freqs


def test_station_forbidden_frequency_is_excluded() -> None:
    candidates = candidate_channels_for_station(_stations()[1], _rules())
    freqs = {round(channel.frequency_mhz, 3) for channel in candidates}
    assert 410.0 not in freqs


def test_validation_accepts_complete_sample() -> None:
    result = validate_inputs(_stations(), _rules())
    assert result["ok"] is True
    assert result["summary"]["station_count"] == 2


def test_optimizer_avoids_same_frequency_for_nearby_stations() -> None:
    result = solve_frequency_assignment(_stations(), _rules())
    assert result["status"] == "success"
    assigned = {item["station_id"]: item["assigned_frequency_mhz"] for item in result["assignments"]}
    assert assigned["S001"] != assigned["S002"]


def test_interference_reports_same_frequency_risk() -> None:
    assignments = [
        {"station_id": "S001", "assigned_frequency_mhz": 410.0, "alternative_frequencies_mhz": "", "risk_score": 0, "risk_level": "低", "notes": ""},
        {"station_id": "S002", "assigned_frequency_mhz": 410.0, "alternative_frequencies_mhz": "", "risk_score": 0, "risk_level": "低", "notes": ""},
    ]
    result = estimate_interference_risk(assignments, _stations(), _rules())
    assert result["summary"]["high_risk_count"] == 1
    assert result["risk_items"][0]["risk_type"] == "同频干扰"


def test_chat_parser_supports_replanning_commands() -> None:
    instruction = parse_chat_instruction("禁用 450 MHz 附近频点，并减少频点数量")
    assert instruction["objective"] == "minimize_frequency_count"
    assert instruction["forbidden_frequencies"] == [450.0]


def test_visualization_data_contains_map_links_and_spectrum() -> None:
    plan = solve_frequency_assignment(_stations(), _rules())
    risks = estimate_interference_risk(plan["assignments"], _stations(), _rules())
    visualization = build_visualization_data(_stations(), _rules(), risks["assignments"], risks["risk_items"])
    assert visualization["summary"]["station_count"] == 2
    assert len(visualization["stations"]) == 2
    assert visualization["spectrum"][0]["candidate_channel_count"] > 0
    assert "risk_distribution" in visualization
