from pydantic import BaseModel, ConfigDict, Field

from backend.domain.models.cv import CVInterviewContext



class CVTextRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	text: str = Field(min_length=1)


class CVTextResponse(BaseModel):
	text: str


class AnonymizationStatusResponse(BaseModel):
	available: bool


class CVParserRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

	anonymized_cv: str = Field(min_length=1)
	selected_position: str = Field(min_length=1)


CVParserResponse = CVInterviewContext