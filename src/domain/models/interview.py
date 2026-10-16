from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewStartMeaningfulness(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	inappropriatezza: int = Field(ge=1, le=3)
	azione: Literal["prosegui", "invita_chiarezza", "blocca"]
	motivazione: str


class InterviewQuestion(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	id: int = Field(ge=1)
	text: str = Field(min_length=10)
	difficulty: Literal["base", "intermedio", "avanzato"]


class InterviewMeaningfulness(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	inappropriatezza: int = Field(ge=1, le=3)
	azione: Literal["prosegui", "invita_chiarezza", "blocca"]
	motivazione: str

	@model_validator(mode="after")
	def action_matches_severity(self) -> "InterviewMeaningfulness":
		expected_action = {
			1: "prosegui",
			2: "invita_chiarezza",
			3: "blocca",
		}[self.inappropriatezza]
		if self.azione != expected_action:
			raise ValueError("L'azione deve corrispondere al livello di inappropriatezza.")
		return self


class InterviewAnswerRadar(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	chiarezza: float = Field(ge=0, le=10)
	pertinenza: float = Field(ge=0, le=10)
	esempi_concreti: float = Field(ge=0, le=10)
	correttezza_tecnica: float = Field(ge=0, le=10)


class InterviewAnswerEvaluation(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	question_id: int = Field(ge=1)
	score: float = Field(ge=0, le=10)
	radar: InterviewAnswerRadar
	comment: str
	better_answer_example: str


class InterviewFinalRadar(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	chiarezza: float = Field(ge=0, le=10)
	pertinenza: float = Field(ge=0, le=10)
	esempi_concreti: float = Field(ge=0, le=10)
	correttezza_tecnica: float = Field(ge=0, le=10)
	comunicazione: float = Field(ge=0, le=10)


class InterviewFinalReport(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	total_score: float = Field(ge=0, le=10)
	radar_scores: InterviewFinalRadar
	strengths: list[str] = Field(min_length=3, max_length=3)
	improvements: list[str] = Field(min_length=3, max_length=3)
	seniority_fit: Literal["sotto", "adeguato", "sopra"]
	next_steps: list[str] = Field(min_length=2, max_length=5)
	questions_to_ask: list[str] = Field(min_length=5, max_length=5)


class InterviewStartTurn(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	turn_id: Literal[0]
	phase: Literal["presentazione"]
	is_final: Literal[False]
	is_meaningful: InterviewStartMeaningfulness
	evaluation_of_previous_answer: None
	next_question: InterviewQuestion
	final_report: None


class InterviewTurn(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	turn_id: int = Field(ge=1)
	phase: Literal["presentazione", "cv", "tecnica", "comportamentale", "finale"]
	is_final: bool
	is_meaningful: InterviewMeaningfulness
	evaluation_of_previous_answer: InterviewAnswerEvaluation
	next_question: InterviewQuestion | None
	final_report: InterviewFinalReport | None

    # model_validator è un campo di validazione dove al suo interno sono presenti delle condizioni da rispettare
	@model_validator(mode="after")
	def validate_turn_state(self) -> "InterviewTurn":
		if self.is_final:
			if self.phase != "finale" or self.next_question is not None or self.final_report is None:
				raise ValueError("Il turno finale richiede fase finale, report e nessuna nuova domanda.")
		else:
			if self.phase == "finale" or self.next_question is None or self.final_report is not None:
				raise ValueError("Un turno intermedio richiede una domanda e non deve includere il report.")
		if self.is_meaningful.azione == "blocca" and not self.is_final:
			raise ValueError("Un turno bloccato deve terminare il colloquio.")
		return self
