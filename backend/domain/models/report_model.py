from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewAnswerReport(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	question: str = Field(min_length=1)
	answer: str = Field(min_length=1)
	motivation: str
	score: int | None = Field(ge=1, le=10)


class InterviewReportRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	history: list[dict[str, str]] = Field(default_factory=list)
	contenuto: str = ""
	answers: list[InterviewAnswerReport] = Field(default_factory=list)
	score: float | None = None

	@model_validator(mode="after")
	def calculate_average_score(self) -> "InterviewReportRequest":
		valid_scores = [
			answer.score for answer in self.answers if answer.score is not None
		]
		self.score = sum(valid_scores) / len(valid_scores) if valid_scores else None
		return self


class InterviewSummary(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	summary: str = Field(min_length=1)
	intervention_points: list["InterviewInterventionPoint"]


class InterviewInterventionPoint(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	area: str = Field(min_length=1)
	evidence: str = Field(min_length=1)
	recommendation: str = Field(min_length=1)


class InterviewReportResponse(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	summary: str
	intervention_points: list[InterviewInterventionPoint]
	contenuto: str
	answers: list[InterviewAnswerReport]
	score: float | None = Field(default=None, ge=1, le=10)
