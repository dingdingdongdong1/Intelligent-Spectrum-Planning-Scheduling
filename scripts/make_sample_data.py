from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "samples"
sys.path.insert(0, str(ROOT))

from backend.app.services.equipment_planning import demo_scenario_records  # noqa: E402


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    stations = []
    base_lat = 31.2304
    base_lon = 121.4737
    for index in range(20):
        service = "专网语音" if index < 12 else "数据链路"
        band = "UHF-A" if index % 2 == 0 else "UHF-B"
        stations.append(
            {
                "station_id": f"S{index + 1:03d}",
                "name": f"演示台站 {index + 1}",
                "latitude": round(base_lat + (index % 5) * 0.018 + (index // 5) * 0.006, 6),
                "longitude": round(base_lon + (index % 4) * 0.019 + (index // 4) * 0.005, 6),
                "service_type": service,
                "bandwidth_khz": 25 if service == "专网语音" else 50,
                "tx_power_w": 20 + (index % 4) * 5,
                "antenna_height_m": 25 + (index % 5) * 3,
                "antenna_gain_dbi": 5 + (index % 3),
                "available_band_group": band,
                "protection_distance_km": 4.5 if service == "专网语音" else 6,
                "priority": 5 if index < 4 else 3 if index < 12 else 2,
                "existing_frequency_mhz": "",
                "forbidden_frequencies_mhz": "450.000" if band == "UHF-B" else "",
            }
        )

    rules = [
        {
            "band_group": "UHF-A",
            "service_type": "专网语音",
            "region": "default",
            "start_mhz": 410,
            "end_mhz": 412,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 50,
            "guard_band_khz": 25,
            "min_spacing_khz": 50,
            "forbidden_frequency_mhz": 411.000,
            "protection_distance_km": 4.5,
        },
        {
            "band_group": "UHF-B",
            "service_type": "专网语音",
            "region": "default",
            "start_mhz": 450,
            "end_mhz": 452,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 50,
            "guard_band_khz": 25,
            "min_spacing_khz": 50,
            "forbidden_frequency_mhz": 450.000,
            "protection_distance_km": 4.5,
        },
        {
            "band_group": "UHF-A",
            "service_type": "数据链路",
            "region": "default",
            "start_mhz": 415,
            "end_mhz": 418,
            "channel_step_khz": 50,
            "max_bandwidth_khz": 50,
            "max_power_w": 40,
            "guard_band_khz": 50,
            "min_spacing_khz": 100,
            "forbidden_frequency_mhz": "",
            "protection_distance_km": 6,
        },
        {
            "band_group": "UHF-B",
            "service_type": "数据链路",
            "region": "default",
            "start_mhz": 455,
            "end_mhz": 458,
            "channel_step_khz": 50,
            "max_bandwidth_khz": 50,
            "max_power_w": 40,
            "guard_band_khz": 50,
            "min_spacing_khz": 100,
            "forbidden_frequency_mhz": "",
            "protection_distance_km": 6,
        },
    ]

    pd.DataFrame(stations).to_excel(SAMPLE_DIR / "stations_sample.xlsx", index=False)
    pd.DataFrame(rules).to_excel(SAMPLE_DIR / "rules_sample.xlsx", index=False)
    task_units, equipment_groups, spectrum_rules = demo_scenario_records()
    pd.DataFrame(task_units).drop(columns=["raw_json"]).to_excel(SAMPLE_DIR / "task_units_sample.xlsx", index=False)
    pd.DataFrame(equipment_groups).drop(columns=["raw_json"]).to_excel(SAMPLE_DIR / "equipment_groups_sample.xlsx", index=False)
    pd.DataFrame(spectrum_rules).drop(columns=["raw_json"]).to_excel(SAMPLE_DIR / "spectrum_rules_sample.xlsx", index=False)
    print(SAMPLE_DIR / "stations_sample.xlsx")
    print(SAMPLE_DIR / "rules_sample.xlsx")
    print(SAMPLE_DIR / "task_units_sample.xlsx")
    print(SAMPLE_DIR / "equipment_groups_sample.xlsx")
    print(SAMPLE_DIR / "spectrum_rules_sample.xlsx")


if __name__ == "__main__":
    main()
