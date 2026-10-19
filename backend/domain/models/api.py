from pydantic import BaseModel, ConfigDict, Field


class CVTextRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	text: str = Field(min_length=1)


class CVTextResponse(BaseModel):
	text: str


class AnonymizationStatusResponse(BaseModel):
	available: bool