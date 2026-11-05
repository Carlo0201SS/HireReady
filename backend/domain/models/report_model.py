from pydantic import BaseModel, ConfigDict, Field


class InterviewAnswerReport(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	question: str = Field(min_length=1)
	answer: str = Field(min_length=1)
	motivation: str
	score: int = Field(ge=1, le=10)


class InterviewReportRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	history: list[dict[str, str]] = Field(default_factory=list)
	contenuto: str = ""
	answers: list[InterviewAnswerReport] = Field(default_factory=list)
	score: int = Field(ge=10)


class InterviewSummary(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	summary: str = Field(min_length=1)


class InterviewReportResponse(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	summary: str
	contenuto: str
	answers: list[InterviewAnswerReport]
	score: int = Field(ge=10)
