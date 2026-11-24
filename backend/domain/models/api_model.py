from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.domain.models.cv_model import CVInterviewContext, CVParsedProfile
from backend.domain.models.interview_model import HireReadyTurn


#-------------CV----------------------------------------
class CVTextRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	text: str = Field(min_length=1)


class CVTextResponse(BaseModel):
	text: str
#---------------------------------------------------------

#--------ANONYMIZATION----------------------------------
class AnonymizationStatusResponse(BaseModel):
	available: bool
	# idle | downloading | loading | ready | error
	state: str = "idle"
#----------------------------------------------------------

#-------CV_PARSER------------------------------------------

class CVParserRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

	anonymized_cv: str = Field(min_length=1)
	selected_position: str = Field(min_length=1)
	position_description: str = ""


CVParserResponse = CVInterviewContext

#--------------------------------------------------------------

#-----INTERVIEW---------------------------------------------------


class InterviewRequest(BaseModel):
	"""Richiesta unica per POST /api/interview.

	- Primo turno:  last_turn=None, candidate_answer=None, history=[],
	                selected_position + profile obbligatori.
	- Turni successivi: last_turn obbligatorio, candidate_answer obbligatoria,
	                history restituita dal server al turno precedente,
	                selected_position + profile ignorati (già nel system prompt
	                dentro `history`).
	- Tutti i turni: anonymized_cv obbligatorio per il controllo di coerenza.
	"""

	model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

	# Stato della sessione (sempre presente)
	history: list[dict[str, str]] = Field(default_factory=list)
	anonymized_cv: str = Field(min_length=1)
	last_turn: HireReadyTurn | None = None

	# Input del turno (opzionale al turno 0)
	candidate_answer: str | None = None

	# Bootstrap (obbligatori solo al turno 0)
	selected_position: str | None = None
	level_position: Literal["junior", "middle", "senior"] | None = None
	position_description: str | None = None
	profile: CVParsedProfile | None = None

	@model_validator(mode="after")
	def _check_turn_payload(self) -> "InterviewRequest":
		is_start = self.last_turn is None

		if is_start:
			if (
				not self.selected_position
				or not self.profile
				or not self.level_position
				or not self.anonymized_cv.strip()
			):
				raise ValueError(
					"Al primo turno servono 'selected_position', 'level_position', "
					"'profile' e 'anonymized_cv'."
				)
			if self.candidate_answer is not None:
				raise ValueError(
					"Al primo turno 'candidate_answer' deve essere null."
				)
		else:
			if not self.candidate_answer or not self.candidate_answer.strip():
				raise ValueError(
					"Nei turni successivi 'candidate_answer' è obbligatoria."
				)
			if (
				self.selected_position is not None
				or self.level_position is not None
				or self.position_description is not None
				or self.profile is not None
			):
				raise ValueError(
					"'selected_position', 'level_position', 'position_description' e 'profile' "
					"vanno inviati solo al primo turno."
				)
		return self

class InterviewTurnRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	history: list[dict[str, str]]
	last_turn: HireReadyTurn | None = None
	candidate_answer: str = Field(min_length=1)


class InterviewTurnResponse(BaseModel):
	turn: HireReadyTurn
	history: list[dict[str, str]]
	is_closed: bool


class InterviewResponse(BaseModel):
	"""Risposta di POST /api/interview.

	Rimanda al client lo stato aggiornato (history + last_turn) perché
	il backend è stateless: è il client a conservarlo in sessione.
	"""

	turn: HireReadyTurn
	history: list[dict[str, str]]
	is_closed: bool