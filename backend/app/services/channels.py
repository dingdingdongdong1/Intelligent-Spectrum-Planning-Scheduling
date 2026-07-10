from __future__ import annotations

from dataclasses import dataclass

from .excel_io import parse_frequency_list


@dataclass(frozen=True)
class Channel:
    frequency_mhz: float
    band_group: str
    service_type: str
    region: str
    rule_id: int | None
    min_spacing_khz: float
    protection_distance_km: float


def _same_frequency(a: float, b: float, tolerance_mhz: float = 0.0005) -> bool:
    return abs(a - b) <= tolerance_mhz


def generate_channels(rules: list[dict]) -> list[Channel]:
    channels: dict[tuple[str, str, float], Channel] = {}
    forbidden_by_key: dict[tuple[str, str, str], set[float]] = {}
    for rule in rules:
        key = (rule["band_group"], rule["service_type"], rule.get("region") or "default")
        forbidden_by_key.setdefault(key, set())
        forbidden = rule.get("forbidden_frequency_mhz")
        if forbidden is not None:
            forbidden_by_key[key].add(round(float(forbidden), 6))

    for rule in rules:
        start = rule.get("start_mhz")
        end = rule.get("end_mhz")
        step = rule.get("channel_step_khz")
        if start is None or end is None or step is None or step <= 0:
            continue
        guard_mhz = (rule.get("guard_band_khz") or 0) / 1000
        lower = float(start) + guard_mhz
        upper = float(end) - guard_mhz
        freq = lower
        while freq <= upper + 1e-9:
            rounded = round(freq, 6)
            key = (rule["band_group"], rule["service_type"], rule.get("region") or "default")
            if not any(_same_frequency(rounded, item) for item in forbidden_by_key.get(key, set())):
                dedupe_key = (rule["band_group"], rule["service_type"], rounded)
                channels[dedupe_key] = Channel(
                    frequency_mhz=rounded,
                    band_group=rule["band_group"],
                    service_type=rule["service_type"],
                    region=rule.get("region") or "default",
                    rule_id=rule.get("id"),
                    min_spacing_khz=float(rule.get("min_spacing_khz") or 0),
                    protection_distance_km=float(rule.get("protection_distance_km") or 0),
                )
            freq += float(step) / 1000
    return sorted(channels.values(), key=lambda item: (item.band_group, item.service_type, item.frequency_mhz))


def candidate_channels_for_station(station: dict, rules: list[dict]) -> list[Channel]:
    station_forbidden = parse_frequency_list(station.get("forbidden_frequencies_mhz"))
    candidates: list[Channel] = []
    for channel in generate_channels(rules):
        if channel.band_group != station.get("available_band_group"):
            continue
        if channel.service_type != station.get("service_type"):
            continue
        if any(_same_frequency(channel.frequency_mhz, blocked) for blocked in station_forbidden):
            continue
        if not check_regulatory_constraints(station, channel.frequency_mhz, rules)["ok"]:
            continue
        candidates.append(channel)
    return candidates


def check_regulatory_constraints(station: dict, frequency_mhz: float, rules: list[dict]) -> dict:
    errors: list[str] = []
    matching_rules = [
        rule
        for rule in rules
        if rule["band_group"] == station.get("available_band_group")
        and rule["service_type"] == station.get("service_type")
        and rule.get("start_mhz") is not None
        and rule.get("end_mhz") is not None
        and float(rule["start_mhz"]) <= frequency_mhz <= float(rule["end_mhz"])
    ]
    if not matching_rules:
        errors.append(f"频点 {frequency_mhz:.6f} MHz 不在台站 {station.get('station_id')} 的可用频段内")
        return {"ok": False, "errors": errors}

    bandwidth = station.get("bandwidth_khz")
    power = station.get("tx_power_w")
    station_forbidden = parse_frequency_list(station.get("forbidden_frequencies_mhz"))
    if any(_same_frequency(frequency_mhz, blocked) for blocked in station_forbidden):
        errors.append(f"频点 {frequency_mhz:.6f} MHz 属于台站禁用频点")

    rule_ok = False
    for rule in matching_rules:
        if rule.get("forbidden_frequency_mhz") is not None and _same_frequency(frequency_mhz, float(rule["forbidden_frequency_mhz"])):
            continue
        if bandwidth is not None and rule.get("max_bandwidth_khz") is not None and float(bandwidth) > float(rule["max_bandwidth_khz"]):
            continue
        if power is not None and rule.get("max_power_w") is not None and float(power) > float(rule["max_power_w"]):
            continue
        rule_ok = True
        break

    if not rule_ok:
        errors.append("频点、带宽或发射功率不满足结构化规则表约束")
    return {"ok": not errors, "errors": errors}
