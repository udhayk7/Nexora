from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status", examples=["ok"])
    environment: str = Field(..., description="Active environment", examples=["development"])
    version: str = Field(..., description="API version", examples=["0.1.0"])


