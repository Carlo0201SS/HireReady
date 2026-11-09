from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


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
    lingua: str = Field(
        min_length=1,
        description=(
            "Lingua rilevata nella risposta dell'utente appena ricevuta. Usa "
            "esattamente 'Italiano' se la risposta è in italiano; altrimenti "
            "indica la lingua rilevata, per esempio 'Inglese' o 'Francese'."
        ),
    )
    motivazione: str = Field(
        description=(
            "Nei turni da 1 a 10 contiene esclusivamente un consiglio di "
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
    ) -> Literal["presentazione", "cv", "tecnica", "finale"]:
        if 0 <= turn_id <= 2:
            return "cv"
        if turn_id == 3:
            return "presentazione"
        if 4 <= turn_id <= 10:
            return "tecnica"
        if turn_id == 11:
            return "finale"
        raise ValueError("turn_id deve essere compreso tra 0 e 11.")

    turn_id: int = Field(
        ...,
        ge=0,
        le=11,
        description=(
            "Numero del turno corrente: 0-2=cv, 3=presentazione, "
            "4-10=tecnica, 11=finale."
        ),
    )
    phase: Literal["presentazione", "cv", "tecnica", "finale"]
    is_final: bool = Field(
        description=(
            "True solo quando il colloquio è terminato secondo le sue fasi; "
            "non usarlo per risposte errate, vaghe o non pertinenti."
        )
    )
    is_meaningful: IsMeaningful | None
    evaluation_of_previous_answer: EvaluationOfPreviousAnswer | None
    next_question: NextQuestion | None

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
        if self.turn_id == 11 and self.evaluation_of_previous_answer is not None:
            raise ValueError(
                "Al turno 11 evaluation_of_previous_answer deve essere null."
            )
        if (
            0 < self.turn_id < 11
            and self.evaluation_of_previous_answer is None
        ):
            raise ValueError(
                "evaluation_of_previous_answer è obbligatoria dopo il turno "
                "iniziale e fino al turno 10, e deve contenere uno score da 1 a 10."
            )

        expected_phase = self.expected_phase(self.turn_id)
        is_blocked = (
            self.is_meaningful is not None
            and self.is_meaningful.azione == "blocca"
        )

        # La moderazione può chiudere il colloquio prima del turno 11.
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
            if self.turn_id != 11 or self.next_question is not None:
                raise ValueError(
                    "is_final=True è ammesso solo al turno 11, con "
                    "next_question=null."
                )
        else:
            if self.turn_id == 11:
                raise ValueError(
                    "Al turno 11 is_final deve essere true."
                )
            if self.next_question is None:
                raise ValueError(
                    "Se is_final=False, next_question è obbligatoria."
                )
        return self
