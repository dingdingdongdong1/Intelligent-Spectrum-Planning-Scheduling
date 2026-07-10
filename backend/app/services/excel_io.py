from __future__ import annotations

import io
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


STATION_COLUMNS = [
    "station_id",
    "name",
    "latitude",
    "longitude",
    "service_type",
    "bandwidth_khz",
    "tx_power_w",
    "antenna_height_m",
    "antenna_gain_dbi",
    "available_band_group",
    "protection_distance_km",
    "priority",
    "existing_frequency_mhz",
    "forbidden_frequencies_mhz",
]

RULE_COLUMNS = [
    "band_group",
    "service_type",
    "region",
    "start_mhz",
    "end_mhz",
    "channel_step_khz",
    "max_bandwidth_khz",
    "max_power_w",
    "guard_band_khz",
    "min_spacing_khz",
    "forbidden_frequency_mhz",
    "protection_distance_km",
]

TASK_UNIT_COLUMNS = [
    "task_unit_id",
    "name",
    "unit_type",
    "area_center_lat",
    "area_center_lon",
    "area_radius_km",
    "priority",
    "spectrum_relation",
    "preferred_band_groups",
    "min_satisfaction_ratio",
]

EQUIPMENT_GROUP_COLUMNS = [
    "equipment_group_id",
    "task_unit_id",
    "equipment_type",
    "count",
    "tx_rx_role",
    "mobility",
    "bandwidth_khz",
    "tx_power_w",
    "antenna_gain_dbi",
    "antenna_height_m",
    "receiver_sensitivity_dbm",
    "modulation",
    "duplex_mode",
    "required_channels",
    "assignment_mode",
    "preferred_band_group",
    "priority",
    "protection_distance_km",
    "min_spacing_khz",
    "guard_band_khz",
]

SPECTRUM_RULE_COLUMNS = [
    "rule_id",
    "rule_type",
    "band_group",
    "spectrum_relation",
    "start_mhz",
    "end_mhz",
    "channel_step_khz",
    "max_bandwidth_khz",
    "max_power_w",
    "guard_band_khz",
    "compatible_unit_types",
    "compatible_equipment_types",
    "reason",
    "source",
    "severity",
]


@dataclass
class ParsedTable:
    records: list[dict[str, Any]]
    missing_columns: list[str]
    extra_columns: list[str]


def _read_excel(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _none_if_empty(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _to_float(value: Any) -> float | None:
    value = _none_if_empty(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any, default: int = 1) -> int:
    value = _none_if_empty(value)
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_frequency_list(value: Any) -> list[float]:
    value = _none_if_empty(value)
    if value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    parts = re.split(r"[,;，；\s]+", str(value).strip())
    parsed: list[float] = []
    for part in parts:
        if not part:
            continue
        try:
            parsed.append(float(part))
        except ValueError:
            continue
    return parsed


def _row_to_station(row: dict[str, Any]) -> dict[str, Any]:
    station_id = _none_if_empty(row.get("station_id"))
    return {
        "station_id": str(station_id) if station_id is not None else "",
        "name": str(_none_if_empty(row.get("name")) or station_id or ""),
        "latitude": _to_float(row.get("latitude")),
        "longitude": _to_float(row.get("longitude")),
        "service_type": _none_if_empty(row.get("service_type")),
        "bandwidth_khz": _to_float(row.get("bandwidth_khz")),
        "tx_power_w": _to_float(row.get("tx_power_w")),
        "antenna_height_m": _to_float(row.get("antenna_height_m")),
        "antenna_gain_dbi": _to_float(row.get("antenna_gain_dbi")),
        "available_band_group": _none_if_empty(row.get("available_band_group")),
        "protection_distance_km": _to_float(row.get("protection_distance_km")),
        "priority": _to_int(row.get("priority"), default=1),
        "existing_frequency_mhz": _to_float(row.get("existing_frequency_mhz")),
        "forbidden_frequencies_mhz": ",".join(str(v) for v in parse_frequency_list(row.get("forbidden_frequencies_mhz"))),
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }


def _row_to_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "band_group": str(_none_if_empty(row.get("band_group")) or ""),
        "service_type": str(_none_if_empty(row.get("service_type")) or ""),
        "region": str(_none_if_empty(row.get("region")) or "default"),
        "start_mhz": _to_float(row.get("start_mhz")),
        "end_mhz": _to_float(row.get("end_mhz")),
        "channel_step_khz": _to_float(row.get("channel_step_khz")),
        "max_bandwidth_khz": _to_float(row.get("max_bandwidth_khz")),
        "max_power_w": _to_float(row.get("max_power_w")),
        "guard_band_khz": _to_float(row.get("guard_band_khz")) or 0,
        "min_spacing_khz": _to_float(row.get("min_spacing_khz")) or 0,
        "forbidden_frequency_mhz": _to_float(row.get("forbidden_frequency_mhz")),
        "protection_distance_km": _to_float(row.get("protection_distance_km")) or 0,
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }


def _row_to_task_unit(row: dict[str, Any]) -> dict[str, Any]:
    task_unit_id = _none_if_empty(row.get("task_unit_id"))
    return {
        "task_unit_id": str(task_unit_id) if task_unit_id is not None else "",
        "name": str(_none_if_empty(row.get("name")) or task_unit_id or ""),
        "unit_type": str(_none_if_empty(row.get("unit_type")) or ""),
        "area_center_lat": _to_float(row.get("area_center_lat")),
        "area_center_lon": _to_float(row.get("area_center_lon")),
        "area_radius_km": _to_float(row.get("area_radius_km")) or 0,
        "priority": _to_int(row.get("priority"), default=1),
        "spectrum_relation": str(_none_if_empty(row.get("spectrum_relation")) or "独占"),
        "preferred_band_groups": str(_none_if_empty(row.get("preferred_band_groups")) or ""),
        "min_satisfaction_ratio": _to_float(row.get("min_satisfaction_ratio")) or 1.0,
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }


def _row_to_equipment_group(row: dict[str, Any]) -> dict[str, Any]:
    equipment_group_id = _none_if_empty(row.get("equipment_group_id"))
    return {
        "equipment_group_id": str(equipment_group_id) if equipment_group_id is not None else "",
        "task_unit_id": str(_none_if_empty(row.get("task_unit_id")) or ""),
        "equipment_type": str(_none_if_empty(row.get("equipment_type")) or ""),
        "count": _to_int(row.get("count"), default=1),
        "tx_rx_role": str(_none_if_empty(row.get("tx_rx_role")) or "双工"),
        "mobility": str(_none_if_empty(row.get("mobility")) or "固定"),
        "bandwidth_khz": _to_float(row.get("bandwidth_khz")) or 25,
        "tx_power_w": _to_float(row.get("tx_power_w")) or 1,
        "antenna_gain_dbi": _to_float(row.get("antenna_gain_dbi")) or 0,
        "antenna_height_m": _to_float(row.get("antenna_height_m")) or 1,
        "receiver_sensitivity_dbm": _to_float(row.get("receiver_sensitivity_dbm")) or -100,
        "modulation": str(_none_if_empty(row.get("modulation")) or ""),
        "duplex_mode": str(_none_if_empty(row.get("duplex_mode")) or "单工"),
        "required_channels": _to_int(row.get("required_channels"), default=1),
        "assignment_mode": str(_none_if_empty(row.get("assignment_mode")) or "离散信道"),
        "preferred_band_group": str(_none_if_empty(row.get("preferred_band_group")) or ""),
        "priority": _to_int(row.get("priority"), default=1),
        "protection_distance_km": _to_float(row.get("protection_distance_km")) or 0,
        "min_spacing_khz": _to_float(row.get("min_spacing_khz")) or 0,
        "guard_band_khz": _to_float(row.get("guard_band_khz")) or 0,
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }


def _row_to_spectrum_rule(row: dict[str, Any]) -> dict[str, Any]:
    rule_id = _none_if_empty(row.get("rule_id"))
    return {
        "rule_id": str(rule_id) if rule_id is not None else "",
        "rule_type": str(_none_if_empty(row.get("rule_type")) or "可用"),
        "band_group": str(_none_if_empty(row.get("band_group")) or ""),
        "spectrum_relation": str(_none_if_empty(row.get("spectrum_relation")) or "可复用"),
        "start_mhz": _to_float(row.get("start_mhz")) or 0,
        "end_mhz": _to_float(row.get("end_mhz")) or 0,
        "channel_step_khz": _to_float(row.get("channel_step_khz")) or 25,
        "max_bandwidth_khz": _to_float(row.get("max_bandwidth_khz")) or 25,
        "max_power_w": _to_float(row.get("max_power_w")) or 1,
        "guard_band_khz": _to_float(row.get("guard_band_khz")) or 0,
        "compatible_unit_types": str(_none_if_empty(row.get("compatible_unit_types")) or ""),
        "compatible_equipment_types": str(_none_if_empty(row.get("compatible_equipment_types")) or ""),
        "reason": str(_none_if_empty(row.get("reason")) or ""),
        "source": str(_none_if_empty(row.get("source")) or ""),
        "severity": str(_none_if_empty(row.get("severity")) or "中"),
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }


def parse_station_excel(file_bytes: bytes) -> ParsedTable:
    df = _normalize_columns(_read_excel(file_bytes))
    missing = [col for col in STATION_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in STATION_COLUMNS]
    for col in missing:
        df[col] = None
    records = [_row_to_station({k: _none_if_empty(v) for k, v in row.items()}) for row in df[STATION_COLUMNS].to_dict("records")]
    records = [record for record in records if record["station_id"] or record["name"]]
    return ParsedTable(records=records, missing_columns=missing, extra_columns=extra)


def parse_rule_excel(file_bytes: bytes) -> ParsedTable:
    df = _normalize_columns(_read_excel(file_bytes))
    missing = [col for col in RULE_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in RULE_COLUMNS]
    for col in missing:
        df[col] = None
    records = [_row_to_rule({k: _none_if_empty(v) for k, v in row.items()}) for row in df[RULE_COLUMNS].to_dict("records")]
    records = [record for record in records if record["band_group"] or record["service_type"]]
    return ParsedTable(records=records, missing_columns=missing, extra_columns=extra)


def parse_task_unit_excel(file_bytes: bytes) -> ParsedTable:
    df = _normalize_columns(_read_excel(file_bytes))
    missing = [col for col in TASK_UNIT_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in TASK_UNIT_COLUMNS]
    for col in missing:
        df[col] = None
    records = [_row_to_task_unit({k: _none_if_empty(v) for k, v in row.items()}) for row in df[TASK_UNIT_COLUMNS].to_dict("records")]
    records = [record for record in records if record["task_unit_id"] or record["name"]]
    return ParsedTable(records=records, missing_columns=missing, extra_columns=extra)


def parse_equipment_group_excel(file_bytes: bytes) -> ParsedTable:
    df = _normalize_columns(_read_excel(file_bytes))
    missing = [col for col in EQUIPMENT_GROUP_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in EQUIPMENT_GROUP_COLUMNS]
    for col in missing:
        df[col] = None
    records = [_row_to_equipment_group({k: _none_if_empty(v) for k, v in row.items()}) for row in df[EQUIPMENT_GROUP_COLUMNS].to_dict("records")]
    records = [record for record in records if record["equipment_group_id"] or record["equipment_type"]]
    return ParsedTable(records=records, missing_columns=missing, extra_columns=extra)


def parse_spectrum_rule_excel(file_bytes: bytes) -> ParsedTable:
    df = _normalize_columns(_read_excel(file_bytes))
    missing = [col for col in SPECTRUM_RULE_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in SPECTRUM_RULE_COLUMNS]
    for col in missing:
        df[col] = None
    records = [_row_to_spectrum_rule({k: _none_if_empty(v) for k, v in row.items()}) for row in df[SPECTRUM_RULE_COLUMNS].to_dict("records")]
    records = [record for record in records if record["rule_id"] or record["band_group"]]
    return ParsedTable(records=records, missing_columns=missing, extra_columns=extra)


def build_station_template() -> bytes:
    rows = [
        {
            "station_id": "S001",
            "name": "示例台站 1",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "service_type": "专网语音",
            "bandwidth_khz": 25,
            "tx_power_w": 20,
            "antenna_height_m": 35,
            "antenna_gain_dbi": 6,
            "available_band_group": "UHF-A",
            "protection_distance_km": 5,
            "priority": 5,
            "existing_frequency_mhz": "",
            "forbidden_frequencies_mhz": "450.000,450.025",
        }
    ]
    return _dataframe_to_xlsx(pd.DataFrame(rows, columns=STATION_COLUMNS))


def build_rule_template() -> bytes:
    rows = [
        {
            "band_group": "UHF-A",
            "service_type": "专网语音",
            "region": "default",
            "start_mhz": 410,
            "end_mhz": 430,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 50,
            "guard_band_khz": 25,
            "min_spacing_khz": 50,
            "forbidden_frequency_mhz": 420.0,
            "protection_distance_km": 5,
        }
    ]
    return _dataframe_to_xlsx(pd.DataFrame(rows, columns=RULE_COLUMNS))


def build_task_unit_template() -> bytes:
    rows = [
        {
            "task_unit_id": "TU-CMD",
            "name": "指挥通信单元",
            "unit_type": "指挥通信单元",
            "area_center_lat": 31.23,
            "area_center_lon": 121.47,
            "area_radius_km": 8,
            "priority": 9,
            "spectrum_relation": "独占",
            "preferred_band_groups": "VHF-SIM-1,UHF-SIM-1",
            "min_satisfaction_ratio": 0.95,
        }
    ]
    return _dataframe_to_xlsx(pd.DataFrame(rows, columns=TASK_UNIT_COLUMNS))


def build_equipment_group_template() -> bytes:
    rows = [
        {
            "equipment_group_id": "EG-CMD-BASE",
            "task_unit_id": "TU-CMD",
            "equipment_type": "固定基站",
            "count": 2,
            "tx_rx_role": "双工",
            "mobility": "固定",
            "bandwidth_khz": 25,
            "tx_power_w": 40,
            "antenna_gain_dbi": 8,
            "antenna_height_m": 35,
            "receiver_sensitivity_dbm": -112,
            "modulation": "FM/数字窄带",
            "duplex_mode": "双工",
            "required_channels": 2,
            "assignment_mode": "离散信道",
            "preferred_band_group": "UHF-SIM-1",
            "priority": 9,
            "protection_distance_km": 8,
            "min_spacing_khz": 50,
            "guard_band_khz": 25,
        }
    ]
    return _dataframe_to_xlsx(pd.DataFrame(rows, columns=EQUIPMENT_GROUP_COLUMNS))


def build_spectrum_rule_template() -> bytes:
    rows = [
        {
            "rule_id": "SR-UHF-AVAILABLE",
            "rule_type": "可用",
            "band_group": "UHF-SIM-1",
            "spectrum_relation": "可复用",
            "start_mhz": 410,
            "end_mhz": 430,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 50,
            "guard_band_khz": 25,
            "compatible_unit_types": "指挥通信单元,机动通信单元",
            "compatible_equipment_types": "手持终端,车载电台,固定基站,指挥车,中继设备",
            "reason": "仿真 UHF 窄带通信频段池",
            "source": "SIM_PUBLIC_REFERENCE",
            "severity": "低",
        },
        {
            "rule_id": "SR-UHF-FORBIDDEN",
            "rule_type": "禁用",
            "band_group": "UHF-SIM-1",
            "spectrum_relation": "禁用",
            "start_mhz": 418,
            "end_mhz": 418.5,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 0,
            "guard_band_khz": 25,
            "compatible_unit_types": "",
            "compatible_equipment_types": "",
            "reason": "仿真禁用窗口",
            "source": "SIM_PUBLIC_REFERENCE",
            "severity": "高",
        },
    ]
    return _dataframe_to_xlsx(pd.DataFrame(rows, columns=SPECTRUM_RULE_COLUMNS))


def _dataframe_to_xlsx(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


def parsed_table_to_dict(table: ParsedTable) -> dict[str, Any]:
    data = asdict(table)
    return data
