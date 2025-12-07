from typing import Dict, Any, Tuple
from typing_extensions import Literal
from datetime import date
from pydantic import BaseModel


class CropStage(BaseModel):
    probability: float
    frostProbabilityIndex: float
    lt10: float
    lt90: float
    parameterA: float
    parameterB: float


class Crop(BaseModel):
    name: str
    variety: str
    stages: Dict[str, CropStage]

# deprecated
# class CimisRaw(BaseModel):
#     # If you know the exact CIMIS schema, replace `dict` with real fields.
#     __root__: Dict[str, Any]
#

class CimisData(BaseModel):
    stationId: str
    stationName: str
    date: date
    airTempMin: float
    airTempMax: float
    dewPointMin: float
    dewPointMax: float
    humidityMin: int
    humidityMax: int
    windSpeedAvg: float
    et0: float
    raw: Dict[str, Any]  # or CimisRaw if you want a wrapper


class FeatureProperties(BaseModel):
    temp: float
    riskLevel: str
    location: str
    crop: Crop
    cimis: CimisData


class PointGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Tuple[float, float]


class FrostRiskFeature(BaseModel):
    type: Literal["Feature"]
    properties: FeatureProperties
    geometry: PointGeometry
