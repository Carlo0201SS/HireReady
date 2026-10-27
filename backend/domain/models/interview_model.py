from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator, ConfigDict


class CVInterviewInput(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

	selected_position: str = Field(min_length=1)
	profile: CVParsedProfile

class CVParsedProfile(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	professional_summary: str = Field(description="Sintesi del profilo ricavata dal CV.")
	technical_skills: list[str] = Field(description="Competenze tecniche esplicitamente presenti nel CV.")
	relevant_experience: list[str] = Field(description="Esperienze e progetti rilevanti, senza inventare dettagli.")
	education: list[str] = Field(description="Formazione esplicitamente presente nel CV.")
	certifications: list[str] = Field(description="Certificazioni esplicitamente presenti nel CV.")
	interview_focus: list[str] = Field(description="Aree del CV utili per un colloquio sulla posizione scelta.")

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enum / Literal types (utili anche fuori dai modelli)
# ---------------------------------------------------------------------------
Phase = Literal["presentazione", "cv", "tecnica", "finale"]
Azione = Literal["prosegui", "invita_chiarezza", "blocca"]


# ---------------------------------------------------------------------------
# Sotto-modelli
# ---------------------------------------------------------------------------
class IsMeaningful(BaseModel):
    """Valutazione di appropriatezza della risposta del candidato."""

    inappropriatezza: int = Field(
        ...,
        ge=1,
        le=3,
        description=(
            "1 = gentile e attinente; 2 = fuori contesto; "
            "3 = derisoria/offensiva/intimidatoria."
        ),
    )
    azione: Azione
    motivazione: str

    @model_validator(mode="after")
    def _check_azione_coerente(self) -> "IsMeaningful":
        # Riproduce i vincoli allOf/if-then dello schema JSON
        mapping = {
            1: "prosegui",
            2: "invita_chiarezza",
            3: "blocca",
        }
        atteso = mapping[self.inappropriatezza]
        if self.azione != atteso:
            raise ValueError(
                f"azione '{self.azione}' non coerente con "
                f"inappropriatezza={self.inappropriatezza} "
                f"(atteso: '{atteso}')"
            )
        return self





class EvaluationOfPreviousAnswer(BaseModel):
    """Valutazione della risposta del candidato al turno precedente."""

    question_id: int
    score: float = Field(..., ge=1, le=3)
    pertinenza: float = Field(..., ge=1, le=3)
    comment: str


class NextQuestion(BaseModel):
    """Prossima domanda da porre al candidato."""

    id: int = Field(..., ge=1, description="Numero progressivo della domanda.")
    text: str = Field(..., min_length=10, description="Testo della domanda.")


# ---------------------------------------------------------------------------
# Modello principale
# ---------------------------------------------------------------------------
class HireReadyTurn(BaseModel):
    """Un singolo turno del colloquio HireReady."""

    turn_id: int = Field(
        ...,
        ge=0,
        description=(
            "Numero del turno corrente. 0 = inizio colloquio "
            "(nessuna risposta da valutare)."
        ),
    )
    phase: Phase
    is_final: bool
    is_meaningful: IsMeaningful
    evaluation_of_previous_answer: Optional[EvaluationOfPreviousAnswer] = None
    next_question: Optional[NextQuestion] = None

    @model_validator(mode="after")
    def _check_coerenza_finale(self) -> "HireReadyTurn":
        # is_final=True  =>  phase='finale' e next_question=None
        # is_final=False =>  next_question obbligatoria
        if self.is_final:
            if self.phase != "finale":
                raise ValueError(
                    "Se is_final=True, phase deve essere 'finale'."
                )
            if self.next_question is not None:
                raise ValueError(
                    "Se is_final=True, next_question deve essere null."
                )
        else:
            if self.phase == "finale":
                raise ValueError(
                    "phase='finale' richiede is_final=True."
                )
            if self.next_question is None:
                raise ValueError(
                    "Se is_final=False, next_question è obbligatoria."
                )
        return self
