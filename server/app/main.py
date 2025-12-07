from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from typing import List
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session

from .schemas import (
    FrostRiskFeature,
    FeatureProperties,
    Crop,
    CropStage,
    CimisData,
    PointGeometry,
)
from .database import get_db, init_db
from .mathModel import (
    compute_frost_risk_from_cimis,
    ALMOND_LT_CONFIG,
    get_damage_parameters,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    init_db()  # creates SQLite file + tables if missing

    yield


app = FastAPI(title="Frost Risk API", version="0.1.0",lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/frost-risk", response_model=FrostRiskFeature)
def get_frost_risk(
    lat: float = Query(..., description="Latitude in decimal degrees"),
    lon: float = Query(..., description="Longitude in decimal degrees"),
    date_param: date = Query(..., alias="date", description="ISO date YYYY-MM-DD"),
    crop: str = Query(..., description="Crop name, e.g., 'almond'"),
    variety: str = Query(..., description="Variety name, e.g., 'nonpareil'"),
    station_id: str | None = Query(None, alias="stationId"),
    db: Session = Depends(get_db),
):
    """
    Return frost risk information as a GeoJSON Feature for the given location/crop/date.
    Now wired to real CIMIS + frost model.
    """

    # For now we only have almond LT config
    if crop.lower() != "almond":
        raise HTTPException(
            status_code=400,
            detail="Only 'almond' crop is supported right now.",
        )

    station = station_id or "145"

    # 1) Call frost model (hourly records)
    records: List[dict] = compute_frost_risk_from_cimis(
        stations=[station],
        start_date=date_param.isoformat(),
        end_date=date_param.isoformat(),
        delta_orchard_c=1.0,
        db=db,
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No CIMIS data found for requested station/date.",
        )

    # Filter just in case multiple stations are returned
    records = [r for r in records if str(r["station"]) == str(station)]
    if not records:
        raise HTTPException(
            status_code=404,
            detail="No records for requested station.",
        )

    # 2) Aggregate to daily summaries
    temps = [r["air_temperature_c"] for r in records if r["air_temperature_c"] is not None]
    rhs = [r["relative_humidity"] for r in records if r["relative_humidity"] is not None]
    dew_points = [r.get("dew_point_c") for r in records if r.get("dew_point_c") is not None]

    air_min = min(temps) if temps else 0.0
    air_max = max(temps) if temps else 0.0
    hum_min = int(min(rhs)) if rhs else 0
    hum_max = int(max(rhs)) if rhs else 0
    dew_min = min(dew_points) if dew_points else 0.0
    dew_max = max(dew_points) if dew_points else 0.0

    # 3) Aggregate damage per stage across the night
    max_damage_overall = 0.0
    crop_stages: dict[str, CropStage] = {}

    for stage_name, stage_lt in ALMOND_LT_CONFIG.stages.items():
        stage_probs: List[float] = []
        for r in records:
            s_info = r["stages"].get(stage_name)
            if s_info:
                stage_probs.append(s_info["damage_prob"])
        if stage_probs:
            p = max(stage_probs)
        else:
            p = 0.0

        max_damage_overall = max(max_damage_overall, p)

        a, b = get_damage_parameters(stage_name)
        display_name = stage_name.capitalize()

        crop_stages[display_name] = CropStage(
            probability=p,
            frostProbabilityIndex=p,  # for now, identical
            lt10=stage_lt.lt10_c,
            lt90=stage_lt.lt90_c,
            parameterA=a,
            parameterB=b,
        )

    # 4) Map overall damage to qualitative risk level
    if max_damage_overall < 0.3:
        risk_level = "low"
    elif max_damage_overall < 0.6:
        risk_level = "moderate"
    else:
        risk_level = "high"

    # 5) Build CimisData block
    cimis_data = CimisData(
        stationId=str(station),
        stationName=f"CIMIS Station {station}",
        date=date_param,
        airTempMin=air_min,
        airTempMax=air_max,
        dewPointMin=dew_min,
        dewPointMax=dew_max,
        humidityMin=hum_min,
        humidityMax=hum_max,
        windSpeedAvg=0.0,  # placeholder – could be added from CIMIS later
        et0=0.0,           # placeholder – same
        raw={"records": records},
    )

    crop_obj = Crop(
        name=crop,
        variety=variety,
        stages=crop_stages,
    )

    props = FeatureProperties(
        temp=air_min,
        riskLevel=risk_level,
        location="Unknown",  # could be improved with reverse geocoding later
        crop=crop_obj,
        cimis=cimis_data,
    )

    geometry = PointGeometry(
        type="Point",
        coordinates=(lon, lat),
    )

    feature = FrostRiskFeature(
        type="Feature",
        properties=props,
        geometry=geometry,
    )

    return feature
