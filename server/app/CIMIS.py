from __future__ import annotations

from datetime import datetime, date
from typing import Any, Iterable, Literal, Dict, List

from sqlalchemy.orm import Session

from .models import CimisHourly


def _normalize_station_list(stations: int | str | Iterable[int | str]) -> List[str]:
    """
    Normalize stations argument into a list of strings.
    """
    if isinstance(stations, (list, tuple, set)):
        return [str(s) for s in stations]
    return [str(stations)]


def _parse_iso_date(d: str | date) -> date:
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(d).date()


def get_cimis_data(
    db: Session | None,
    stations: int | str | Iterable[int | str],
    start_date: str,
    end_date: str,
    data_items: str | Iterable[str] | None = None,
    *,
    unit: Literal["M", "E"] = "M",
    scope: Literal["daily", "hourly", "both"] = "hourly",
    prioritize_scs: bool | None = None,
    use_cache: bool = True,
    max_age: None | Any = None,
) -> dict:
    """
    DB-backed replacement for the old CIMIS API call.

    It reads from CimisHourly and builds a JSON structure that looks like
    the CIMIS hourly response, so existing code (cimis_json_to_records)
    keeps working without changes.

    NOTE: This is READ-ONLY; it never writes to the DB.
    """
    if db is None:
        raise ValueError("get_cimis_data(db=...) requires a valid SQLAlchemy Session")

    # For now we only support hourly scope from DB
    if scope not in ("hourly", "both"):
        raise ValueError("DB-backed get_cimis_data currently only supports scope='hourly' or 'both'")

    station_ids = _normalize_station_list(stations)
    start = _parse_iso_date(start_date)
    end = _parse_iso_date(end_date)

    # Query all matching hourly rows
    rows: List[CimisHourly] = (
        db.query(CimisHourly)
        .filter(
            CimisHourly.station_id.in_(station_ids),
            CimisHourly.date >= start,
            CimisHourly.date <= end,
        )
        .order_by(CimisHourly.station_id, CimisHourly.date, CimisHourly.hour)
        .all()
    )

    # Build CIMIS-like JSON: Data -> Providers -> [ { Records: [...] } ]
    records: List[Dict[str, Any]] = []

    for r in rows:
        # CIMIS-style "Date": "YYYY-MM-DD"
        date_str = r.date.isoformat()

        # CIMIS hourly uses "0100", "0200", ...; we reconstruct that from hour int
        if r.hour is None:
            continue
        hour_str = f"{int(r.hour):02d}00"

        rec: Dict[str, Any] = {
            "Station": str(r.station_id),
            "Date": date_str,
            "Hour": hour_str,
        }

        # Only include items we actually have. Names are chosen so that
        # cimis_json_to_records() can find them via _get_cimis_value(...).
        # It expects keys like "HlyAirTmp" and "HlyRelHum" with {"Value": "..."}.
        if r.air_temp is not None:
            rec["HlyAirTmp"] = {"Value": f"{r.air_temp:.2f}", "Qc": "V", "Unit": "(C)"}
        if r.humidity is not None:
            rec["HlyRelHum"] = {"Value": f"{int(r.humidity)}", "Qc": "V", "Unit": "(%)"}

        # You can extend this later for more items if needed.
        # E.g., dew point, wind speed, etc., mapped to whatever keys you want.

        records.append(rec)

    payload: Dict[str, Any] = {
        "Data": {
            "Providers": [
                {
                    "Name": "local-db",
                    "Type": "station",
                    "Owner": "frostbyte",
                    "Records": records,
                }
            ]
        }
    }

    return payload
