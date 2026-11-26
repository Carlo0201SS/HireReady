from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


try:
    FINAL_TURN_ID = int(os.getenv("HIREREADY_FINAL_TURN_ID", "20"))
except ValueError as error:
    raise RuntimeError("HIREREADY_FINAL_TURN_ID deve essere un numero intero.") from error

if FINAL_TURN_ID < 12:
    raise RuntimeError("HIREREADY_FINAL_TURN_ID deve essere almeno 12.")

CV_FIRST_TURN_ID = 0
CV_LAST_TURN_ID = 4
CAREER_FIRST_TURN_ID = 5
CAREER_LAST_TURN_ID = 10
TECHNICAL_FIRST_TURN_ID = 11


class StrictModel(BaseModel):
    """Vieta campi extra: lo schema JSON avra' additionalProperties=false,
    cosi' il decoding vincolato di LM Studio non puo' inventare chiavi."""

    model_config = ConfigDict(extra="forbid")






# ---------------------------------------------------------------------------
# Sotto-modelli
# ---------------------------------------------------------------------------
class IsMeaningful(StrictModel):
    """Classificazione della risposta e della lingua usata dal candidato."""

    azione: Literal["prosegui", "blocca"] = Field(
        description=(
            "'blocca' se la risposta non è in italiano oppure contiene volgarità "
            "o insulti diretti; altrimenti usare 'prosegui'."
        )
    )

    motivazione: str = Field(
        description=(
            f"Nei turni da 1 a {FINAL_TURN_ID - 1} contiene esclusivamente un consiglio di "
            "miglioramento breve, concreto e specifico, preferibilmente in una "
            "sola frase; vale anche per risposte di alta qualità. Se azione='blocca', "
            "indica brevemente il motivo del blocco."
        )
    )

    #@model_validator(mode="after")
    #def _check_azione_coerente(self) -> "IsMeaningful":
        # Riproduce i vincoli allOf/if-then dello schema JSON
    #    mapping = {
    #        1: "prosegui",
    #        2: "invita_chiarezza",
    #        3: "blocca",
    #    }
    #    atteso = mapping[self.inappropriatezza]
    #    if self.azione != atteso:
    #        raise ValueError(
    #            f"azione '{self.azione}' non coerente con "
    #            f"inappropriatezza={self.inappropriatezza} "
    #            f"(atteso: '{atteso}')"
    #        )
    #    return self


class EvaluationOfPreviousAnswer(StrictModel):
    """Valutazione numerica della risposta appena fornita dal candidato."""

    score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Punteggio complessivo della risposta, da 1 a 10.",
    )



#class EvaluationOfPreviousAnswer(BaseModel):
#    """Valutazione della risposta del candidato al turno precedente."""
#
#    question_id: int
#    score: float = Field(..., ge=1, le=3) # i tre puntini = campo required.
#    pertinenza: float = Field(..., ge=1, le=3)
#    comment: str


class NextQuestion(StrictModel):
    """Prossima domanda da porre al candidato."""

    id: int = Field(..., ge=1, description="Numero progressivo della domanda.")
    text: str = Field(..., min_length=10, description="Testo della domanda.")


class ProfileConsistencyCheck(StrictModel):
    status: Literal["consistent", "contradiction"]
    current_claim: str = ""
    conflicting_claim: str = ""


def _require_meaningful_after_start(
    turn_id: int,
    is_meaningful: IsMeaningful | None,
) -> None:
    if turn_id > 0 and is_meaningful is None:
        raise ValueError(
            "is_meaningful è obbligatorio dopo il turno iniziale e deve "
            "contenere azione='prosegui' oppure azione='blocca'."
        )


# ---------------------------------------------------------------------------
# Modello principale
# ---------------------------------------------------------------------------
class HireReadyTurn(StrictModel):
    """Un singolo turno del colloquio HireReady."""

    @staticmethod
    def expected_phase(
        turn_id: int,
    ) -> Literal["carriera", "cv", "tecnica", "finale"]:
        if CV_FIRST_TURN_ID <= turn_id <= CV_LAST_TURN_ID:
            return "cv"
        if CAREER_FIRST_TURN_ID <= turn_id <= CAREER_LAST_TURN_ID:
            return "carriera"
        if turn_id == FINAL_TURN_ID:
            return "finale"
        if TECHNICAL_FIRST_TURN_ID <= turn_id < FINAL_TURN_ID:
            return "tecnica"
        raise ValueError(
            f"turn_id deve essere compreso tra 0 e {FINAL_TURN_ID}."
        )

    turn_id: int = Field(
        ...,
        ge=0,
        le=FINAL_TURN_ID,
        description=(
            f"Numero del turno corrente: {CV_FIRST_TURN_ID}-{CV_LAST_TURN_ID}=cv, "
            f"{CAREER_FIRST_TURN_ID}-{CAREER_LAST_TURN_ID}=carriera, "
            f"{TECHNICAL_FIRST_TURN_ID}-{FINAL_TURN_ID - 1}=tecnica, "
            f"{FINAL_TURN_ID}=finale."
        ),
    )
    phase: Literal["carriera", "cv", "tecnica", "finale"]
    is_final: bool = Field(
        description=(
            "True solo quando il colloquio è terminato secondo le sue fasi; "
            "non usarlo per risposte errate, vaghe o non pertinenti."
        )
    )
    is_meaningful: IsMeaningful | None
    evaluation_of_previous_answer: EvaluationOfPreviousAnswer | None
    next_question: NextQuestion | None
    closure_reason: Literal["profile_contradiction"] | None = None
    closure_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_coerenza_finale(
        self,
        info: ValidationInfo,
    ) -> "HireReadyTurn":
        expected_turn_id = (info.context or {}).get("expected_turn_id")
        if expected_turn_id is not None and self.turn_id != expected_turn_id:
            raise ValueError(
                f"Il turno atteso è {expected_turn_id}, ricevuto {self.turn_id}."
            )

        _require_meaningful_after_start(self.turn_id, self.is_meaningful)
        if (
            self.turn_id == FINAL_TURN_ID
            and self.evaluation_of_previous_answer is not None
        ):
            raise ValueError(
                f"Al turno {FINAL_TURN_ID} evaluation_of_previous_answer "
                "deve essere null."
            )
        if (
            0 < self.turn_id < FINAL_TURN_ID
            and self.evaluation_of_previous_answer is None
        ):
            raise ValueError(
                "evaluation_of_previous_answer è obbligatoria dopo il turno "
                f"iniziale e fino al turno {FINAL_TURN_ID - 1}, e deve "
                "contenere uno score da 1 a 10."
            )

        expected_phase = self.expected_phase(self.turn_id)
        is_blocked = (
            self.is_meaningful is not None
            and self.is_meaningful.azione == "blocca"
        )

        if self.closure_reason == "profile_contradiction":
            if not self.is_final or self.phase != "finale" or self.next_question is not None:
                raise ValueError(
                    "La chiusura per contraddizione richiede phase='finale', "
                    "is_final=true e next_question=null."
                )
            if len(self.closure_evidence) < 2:
                raise ValueError(
                    "La chiusura per contraddizione richiede almeno due "
                    "elementi di evidenza."
                )
            return self
        if self.closure_evidence:
            raise ValueError(
                "closure_evidence è ammessa solo per una chiusura "
                "da contraddizione."
            )

        # La moderazione può chiudere il colloquio prima del turno finale.
        if is_blocked and self.is_final:
            if self.phase != "finale" or self.next_question is not None:
                raise ValueError(
                    "La chiusura per linguaggio inappropriato richiede "
                    "phase='finale' e next_question=null."
                )
            return self

        if self.phase != expected_phase:
            raise ValueError(
                f"Per turn_id={self.turn_id}, phase deve essere "
                f"'{expected_phase}'."
            )

        if self.is_final:
            if (
                self.turn_id != FINAL_TURN_ID
                or self.next_question is not None
            ):
                raise ValueError(
                    f"is_final=True è ammesso solo al turno {FINAL_TURN_ID}, con "
                    "next_question=null."
                )
        else:
            if self.turn_id == FINAL_TURN_ID:
                raise ValueError(
                    f"Al turno {FINAL_TURN_ID} is_final deve essere true."
                )
            if self.next_question is None:
                raise ValueError(
                    "Se is_final=False, next_question è obbligatoria."
                )
        return self
