from __future__ import annotations

from collections import Counter

from .channels import candidate_channels_for_station


def validate_inputs(stations: list[dict], rules: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    missing_questions: list[str] = []

    if not stations:
        errors.append("未读取到台站数据")
    if not rules:
        errors.append("未读取到规则数据")

    station_ids = [station.get("station_id") for station in stations if station.get("station_id")]
    for station_id, count in Counter(station_ids).items():
        if count > 1:
            errors.append(f"台站编号重复：{station_id}")

    required_station_fields = [
        "station_id",
        "latitude",
        "longitude",
        "service_type",
        "bandwidth_khz",
        "tx_power_w",
        "available_band_group",
        "protection_distance_km",
        "priority",
    ]
    for station in stations:
        station_label = station.get("station_id") or station.get("name") or "未命名台站"
        for field in required_station_fields:
            if station.get(field) in (None, ""):
                errors.append(f"{station_label} 缺少字段 {field}")
        lat = station.get("latitude")
        lon = station.get("longitude")
        if lat is not None and not (-90 <= float(lat) <= 90):
            errors.append(f"{station_label} 纬度超出范围")
        if lon is not None and not (-180 <= float(lon) <= 180):
            errors.append(f"{station_label} 经度超出范围")
        for positive_field in ["bandwidth_khz", "tx_power_w", "protection_distance_km"]:
            value = station.get(positive_field)
            if value is not None and float(value) < 0:
                errors.append(f"{station_label} 字段 {positive_field} 不能为负数")
        if station.get("priority") is not None and int(station["priority"]) < 1:
            warnings.append(f"{station_label} 优先级小于 1，求解时会按 1 处理")

    required_rule_fields = [
        "band_group",
        "service_type",
        "start_mhz",
        "end_mhz",
        "channel_step_khz",
        "max_bandwidth_khz",
        "max_power_w",
        "min_spacing_khz",
        "protection_distance_km",
    ]
    for index, rule in enumerate(rules, start=1):
        label = f"规则第 {index} 行"
        for field in required_rule_fields:
            if rule.get(field) in (None, ""):
                errors.append(f"{label} 缺少字段 {field}")
        start = rule.get("start_mhz")
        end = rule.get("end_mhz")
        step = rule.get("channel_step_khz")
        if start is not None and end is not None and float(start) >= float(end):
            errors.append(f"{label} 起始频率必须小于终止频率")
        if step is not None and float(step) <= 0:
            errors.append(f"{label} 信道步进必须大于 0")

    if stations and rules:
        for station in stations:
            if station.get("station_id") and station.get("available_band_group") and station.get("service_type"):
                candidates = candidate_channels_for_station(station, rules)
                if not candidates:
                    errors.append(
                        f"{station['station_id']} 没有可用候选频点，请检查频段、业务类型、禁用频点、功率和带宽约束"
                    )

    missing_groups = _build_missing_groups(errors)
    for field, count in missing_groups.items():
        missing_questions.append(f"有 {count} 处缺少 {field}，请补充后重新上传或在聊天中说明默认值。")

    summary = {
        "station_count": len(stations),
        "rule_count": len(rules),
        "service_types": sorted({station.get("service_type") for station in stations if station.get("service_type")}),
        "band_groups": sorted({rule.get("band_group") for rule in rules if rule.get("band_group")}),
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "missing_questions": missing_questions,
        "summary": summary,
    }


def _build_missing_groups(errors: list[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for error in errors:
        if "缺少字段" not in error:
            continue
        field = error.rsplit(" ", 1)[-1]
        counts[field] += 1
    return dict(counts)
