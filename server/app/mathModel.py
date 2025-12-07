from __future__ import annotations

from math import atan, sqrt, exp, log
from dataclasses import dataclass
from typing import Dict, Mapping, Any, Optional, List

from datetime import datetime

from sqlalchemy.orm import Session

from dotenv import load_dotenv, get_key
from .CIMIS import get_cimis_data


@dataclass(frozen=True)
class StageLT:
    """LT thresholds for a single phenological stage (in °C)."""
    lt10_c: float
    lt90_c: float


@dataclass(frozen=True)
class CropLTConfig:
    """All LT thresholds for a given crop across phenological stages."""
    crop_name: str
    stages: Mapping[str, StageLT]  # keys are lowercase stage names

    def stage_names(self) -> tuple[str, ...]:
        return tuple(self.stages.keys())


# Almond configuration
ALMOND_LT_CONFIG = CropLTConfig(
    crop_name="almond",
    stages={
        "pinkbud":   StageLT(lt10_c=-3.5, lt90_c=-5.5),
        "fullbloom": StageLT(lt10_c=-3.0, lt90_c=-4.5),
        "petalfall": StageLT(lt10_c=-2.8, lt90_c=-5.0),
        "fruitset":  StageLT(lt10_c=-2.5, lt90_c=-4.7),
        "smallnut":  StageLT(lt10_c=-2.8, lt90_c=-4.5),
    },
)


# ------------ PHYSICS / BIO FUNCTIONS ------------

def wet_bulb_temperature(temperature_c: float, relative_humidity: float) -> float:
    """
    Approximate wet-bulb temperature from dry-bulb (°C) and RH (%).
    """
    wb = (
        temperature_c * atan(0.151977 * sqrt(relative_humidity + 8.313659))
        + atan(temperature_c + relative_humidity)
        - atan(relative_humidity - 1.676331)
        + 0.00391838 * (relative_humidity ** 1.5) * atan(0.023101 * relative_humidity)
        - 4.686035
    )
    return wb


def blossom_temp(
    temperature_c: float,
    relative_humidity: float,
    delta_orchard_c: float = 1.0,
) -> float:
    """
    Estimate blossom temperature from air temperature and RH.
    """
    wb = wet_bulb_temperature(temperature_c, relative_humidity)
    temp_bud = temperature_c - delta_orchard_c - (temperature_c - wb)
    return temp_bud


def cooling_rate(
    temperature_prev_c: float,
    temperature_c: float,
    delta_t_hours: float,
) -> float:
    """
    Cooling rate (°C per hour) from previous temp to current temp.
    """
    if delta_t_hours == 0:
        return 0.0
    return (temperature_prev_c - temperature_c) / delta_t_hours


def dew_point_temperature(temperature_c: float, relative_humidity: float) -> float:
    """
    Approximate dew point (°C) from air temperature (°C) and RH (%).
    Magnus formula.
    """
    if relative_humidity <= 0:
        return temperature_c  # fallback
    a = 17.27
    b = 237.7
    gamma = (a * temperature_c / (b + temperature_c)) + log(relative_humidity / 100.0)
    td = (b * gamma) / (a - gamma)
    return td


def get_damage_parameters(stage: str):
    """
    Logistic curve parameters per stage.
    """
    s = stage.lower()
    if s == "pinkbud":
        a, b = 10.0, 1.5
    elif s == "fullbloom":
        a, b = 9.0, 1.4
    elif s == "petalfall":
        a, b = 8.0, 1.3
    elif s == "fruitset":
        a, b = 7.0, 1.2
    elif s == "smallnut":
        a, b = 6.0, 1.1
    else:
        raise ValueError(f"Invalid phenological stage: {stage}")
    return a, b


def damage_curve(temp_c: float, stage: str) -> float:
    """
    Logistic frost damage probability (0–1) at given temp and stage.
    """
    a, b = get_damage_parameters(stage)
    z = a + b * temp_c
    p = 1.0 / (1.0 + exp(-z))
    return p


def estimate_damage_at_temperature(temperature_c: float, stage: str) -> float:
    """
    Convenience wrapper: damage probability 0–1 at given temp and stage.
    """
    return damage_curve(temperature_c, stage)


# ------------ CIMIS JSON FLATTENING ------------

def _get_cimis_value(rec: Dict[str, Any], *keys: str) -> Optional[float]:
    """
    Extract a numeric CIMIS value from any of the given keys.

    CIMIS hourly JSON in your test data uses keys like "HlyAirTmp", "HlyRelHum",
    each shaped as: {"Value": "12.3", "Qc": "V", "Unit": "..."}.
    """
    for key in keys:
        obj = rec.get(key)
        if not isinstance(obj, dict):
            continue
        v = obj.get("Value")
        if v in ("", None):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            continue
    return None


def cimis_json_to_records(raw_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten CIMIS JSON (from get_cimis_data) into a list of dicts.
    One dict per hourly record.

    Each record contains:
      station, date, hour, timestamp, air_temp_c, rel_hum
    """

    providers = raw_json.get("Data", {}).get("Providers", [])
    rows: List[Dict[str, Any]] = []

    for provider in providers:
        for rec in provider.get("Records", []):
            # In your real hourly JSON, Station is on the record:
            #   "Station": "170"
            station = rec.get("Station") or provider.get("Station", {}).get("StationNbr")

            date_str = rec.get("Date")
            hour_raw = rec.get("Hour")
            if date_str is None or hour_raw is None:
                continue

            # CIMIS hourly uses "0100", "0200", ...; convert to "01", "02" etc.
            hour_raw_str = str(hour_raw)
            if len(hour_raw_str) == 4 and hour_raw_str.endswith("00"):
                hour_str = hour_raw_str[:2]
            else:
                hour_str = hour_raw_str.zfill(2)

            timestamp_str = f"{date_str} {hour_str}:00"

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                # Skip malformed timestamps
                continue

            # Use the *actual* keys from your JSON, with hyphenated fallbacks just in case
            air_temp_c = _get_cimis_value(rec, "HlyAirTmp", "hly-air-tmp")
            rel_hum = _get_cimis_value(rec, "HlyRelHum", "hly-rel-hum")

            row = {
                "station": station,
                "date": date_str,
                "hour": hour_str,
                "timestamp": timestamp,
                "air_temp_c": air_temp_c,
                "rel_hum": rel_hum,
            }
            rows.append(row)

    # sort by station + timestamp to preserve time order
    rows.sort(key=lambda r: (r["station"], r["timestamp"]))
    return rows
# ------------ TOP-LEVEL FROST RISK COMPUTATION ------------

def compute_frost_risk_from_cimis(
    stations,
    start_date: str,
    end_date: str,
    delta_orchard_c: float = 1.0,
    db: Session | None = None,
):
    """
    1) make CIMIS call
    2) parse for air temp + RH (NO DataFrame, just list of dicts)
    3) compute wet-bulb, blossom temp, cooling rate, dew point
    4) calculate frost damage for each almond stage
    5) package everything into JSON-ready Python structures
    """

    data_items = ["hly-air-tmp", "hly-rel-hum"]
    print("entering compute_frost_risk_from_cimis")
    raw_json = get_cimis_data(
        db=db,
        stations=stations,
        start_date=start_date,
        end_date=end_date,
        data_items=data_items,
        unit="M",
        scope="hourly",
    )
    print("got raw_json from get_cimis_data")
    records = cimis_json_to_records(raw_json)
    records = cimis_json_to_records(raw_json)
    print(f"compute_frost_risk_from_cimis: got {len(records)} records "
          f"for stations={stations}, dates={start_date}..{end_date}")
    if not records:
        return []

    # track previous temperature per station for cooling rate
    prev_temp: Dict[Any, Optional[float]] = {}
    prev_time: Dict[Any, Optional[datetime]] = {}

    results = []

    for r in records:
        station = r["station"]
        timestamp = r["timestamp"]
        air_temp = r["air_temp_c"]
        rel_hum = r["rel_hum"]

        # compute wet-bulb, blossom temp, dew point if we have data
        if air_temp is not None and rel_hum is not None:
            wet_bulb_c = wet_bulb_temperature(air_temp, rel_hum)
            blossom_temp_c = blossom_temp(air_temp, rel_hum, delta_orchard_c)
            dew_point_c = dew_point_temperature(air_temp, rel_hum)
        else:
            wet_bulb_c = None
            blossom_temp_c = None
            dew_point_c = None

        # cooling rate (°C/hr) vs previous hour per station
        if station in prev_temp and prev_temp[station] is not None:
            dt_hours = 1.0
            if prev_time.get(station) is not None:
                dt = (timestamp - prev_time[station]).total_seconds() / 3600.0
                if dt > 0:
                    dt_hours = dt
            if air_temp is not None:
                cooling_rate_c_per_hr = (prev_temp[station] - air_temp) / dt_hours
            else:
                cooling_rate_c_per_hr = 0.0
        else:
            cooling_rate_c_per_hr = 0.0

        prev_temp[station] = air_temp
        prev_time[station] = timestamp

        # compute damage per stage if blossom_temp is available
        stage_data: Dict[str, Any] = {}
        if blossom_temp_c is not None:
            for stage_name, stage_lt in ALMOND_LT_CONFIG.stages.items():
                damage_prob = estimate_damage_at_temperature(blossom_temp_c, stage_name)
                stage_data[stage_name] = {
                    "LT10_C": stage_lt.lt10_c,
                    "LT90_C": stage_lt.lt90_c,
                    "damage_prob": damage_prob,
                }

        record_out = {
            "station": station,
            "timestamp": timestamp.isoformat(),
            "air_temperature_c": air_temp,
            "relative_humidity": rel_hum,
            "dew_point_c": dew_point_c,
            "wet_bulb_c": wet_bulb_c,
            "blossom_temp_c": blossom_temp_c,
            "cooling_rate_c_per_hr": cooling_rate_c_per_hr,
            "stages": stage_data,
        }
        results.append(record_out)

    return results

if __name__ == "__main__":
    test_JSON = {
  "Data": {
    "Providers": [
      {
        "Name": "cimis",
        "Type": "station",
        "Owner": "water.ca.gov",
        "Records": [
          {
            "Date": "2010-01-01",
            "Julian": "1",
            "Station": "12",
            "Standard": "english",
            "ZipCodes": "95974, 95958, 95938",
            "Scope": "daily",
            "DayEto": {
              "Value": "0.02",
              "Qc": " ",
              "Unit": "(in)"
            },
            "DayAsceEto": {
              "Value": "0.02",
              "Qc": " ",
              "Unit": "(in)"
            },
            "DayPrecip": {
              "Value": "0.03",
              "Qc": " ",
              "Unit": "(in)"
            }
          }
        ]
      },
      {
        "Name": "cimis",
        "Type": "spatial",
        "Owner": "water.ca.gov",
        "Records": [
          {
            "Date": "2010-01-01",
            "Julian": "1",
            "Standard": "english",
            "ZipCodes": "97544",
            "Scope": "daily",
            "DayAsceEto": {
              "Value": "0.04",
              "Qc": " ",
              "Unit": "(in)"
            }
          }
        ]
      }
    ]
  }
}
    # example usage
    results = compute_frost_risk_from_cimis(
        stations=[2],
        start_date="2024-01-01",
        end_date="2024-01-07",
        delta_orchard_c=1.0,
    )

    import json
    print(json.dumps(results, indent=2, default=str))