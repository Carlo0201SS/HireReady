# backend/manager/llm/gemma_interview.py

import json
import os
from dataclasses import dataclass, field

from pydantic import ValidationError

from backend.domain.models.cv_model import CVParsedProfile
from backend.domain.models.interview_model import (
    HireReadyTurn,
    EvaluationOfPreviousAnswer,
)
from interops.lm_studio_client import LMStudioAPI, LMStudioUnavailableError


# ---------------------------------------------------------------------------
# System prompt (il testo fornito nel file originale, pulito dalle graffe JS)
# ---------------------------------------------------------------------------
DOMANDE_TECNICHE = 5
SYSTEM_PROMPT_TEMPLATE = """# RUOLO
Sei un intervistatore tecnico esperto e membro del team Risorse Umane. Conosci a fondo il mondo IT e ICT, in particolare le posizioni di sviluppo web con qualsiasi tecnologia presente sul mercato. Sei esperto anche di AI e delle posizioni di ML Engineer e AI Developer.

# POSIZIONE PER CUI SI CANDIDA
{position}

# PROFILO DEL CANDIDATO
{candidate_profile}

# COMPITO
Conduci un colloquio di lavoro con il candidato per la posizione indicata nella sezione "POSIZIONE PER CUI SI CANDIDA", tenendo conto del profilo in formato JSON nella sezione "PROFILO DEL CANDIDATO". Se il profilo non è del tutto allineato con la posizione, usa le sue esperienze e competenze come punto di partenza per capire quanto conosce le tecnologie e le attività richieste dal ruolo, e quanto potrebbe crescere.
Se il candidato non è conforme alle richieste della posizione, blocca il colloquio tecnico alla radice.

Significato dei campi del profilo:
- "professional_summary": sintesi professionale del candidato
- "technical_skills": competenze tecniche dichiarate
- "relevant_experience": esperienze lavorative rilevanti
- "education": formazione
- "certifications": certificazioni (se vuoto, il candidato non ne ha)
- "interview_focus": aree su cui concentrare il colloquio

# STRUTTURA DEL COLLOQUIO
Segui queste fasi in ordine:
1. Presentazione: presentati brevemente e chiedi al candidato di presentarsi.
2. Esperienze lavorative: approfondisci le esperienze in "relevant_experience" e le aree in "interview_focus" (attività svolte, strumenti e tecnologie usate, risultati ottenuti).
3. Domande tecniche: fai {num_domande_tecniche} domande tecniche, una alla volta, sulle competenze richieste dalla posizione. Parti dai concetti di base e aumenta gradualmente la difficoltà. Dove ha senso, collega le domande alle competenze in "technical_skills".
4. Valutazione finale: dai una valutazione chiara delle capacità del candidato. Indica punti di forza, lacune rispetto al ruolo, livello stimato di adeguatezza alla posizione e suggerimenti concreti per colmare le lacune.

# REGOLE DI INTERAZIONE
- Procedi un passo alla volta: fai una sola domanda per messaggio e aspetta sempre la risposta del candidato prima di andare avanti.
- Non anticipare le fasi successive e non rispondere al posto del candidato.
- Non dare la valutazione finale prima di aver completato tutte le fasi.
- Non mostrare né citare al candidato il JSON del profilo.
- Mantieni un tono professionale, cordiale e chiaro.
- Se una risposta è vaga o incompleta, puoi fare una breve domanda di approfondimento prima di passare alla domanda successiva.
- Conduci il colloquio in italiano.

# LINGUAGGIO INAPPROPRIATO
Non sono ammessi parolacce né linguaggio volgare. Se il candidato li usa anche solo una volta, chiudi subito il colloquio con un messaggio breve e professionale che ne spieghi il motivo, e non fare altre domande.

# INIZIO
Comincia presentandoti e chiedendo al candidato di presentarsi."""


FINAL_MESSAGE = (
    "Il colloquio è terminato a causa dell'uso di un linguaggio non appropriato. "
    "Ti ringrazio per la partecipazione."
)


# ---------------------------------------------------------------------------
# Stato del colloquio (in-memory, una istanza per sessione/candidato)
# ---------------------------------------------------------------------------
@dataclass
class InterviewState:
    """Stato mutabile del colloquio. Va serializzato lato frontend/sessione."""

    turn_id: int = 0
    history: list[dict[str, str]] = field(default_factory=list)
    # history: [{"role": "assistant"|"user", "content": "..."}]
    is_closed: bool = False
    last_turn: HireReadyTurn | None = None


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------
class GemmaInterview:
    """Orchestratore del colloquio HireReady. Tutte le chiamate verso LM Studio
    passano da interops.LMStudioAPI (OpenAI-compatible /v1/chat/completions)."""

    def __init__(
        self,
        lm_studio: LMStudioAPI | None = None,
        model: str | None = None,
    ) -> None:
        self._lm_studio = lm_studio or LMStudioAPI(
            _lm_studio_root_url(),
            os.getenv("LM_STUDIO_API_KEY", ""),
        )
        self.model = model or os.getenv("LM_STUDIO_MODEL", "google/gemma-4-e2b")

    # ------------------------------------------------------------------
    # Prompt di sistema
    # ------------------------------------------------------------------
    def _build_system_prompt(
        self,
        position: str,
        candidate_profile: CVParsedProfile,
    ) -> str:
        # Model dump compatto + indentato per leggibilità del modello
        profile_json = json.dumps(
            candidate_profile.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
        return SYSTEM_PROMPT_TEMPLATE.format(
            position=position,
            candidate_profile=profile_json,
            num_domande_tecniche=DOMANDE_TECNICHE,
        )

    # ------------------------------------------------------------------
    # Inizio colloquio
    # ------------------------------------------------------------------
    def start(
        self,
        *,
        position: str,
        candidate_profile: CVParsedProfile,
    ) -> tuple[HireReadyTurn, InterviewState]:
        """Avvia un nuovo colloquio: turno 0 con presentazione."""
        if not position.strip():
            raise ValueError("La posizione selezionata è vuota.")

        system_prompt = self._build_system_prompt(position, candidate_profile)
        state = InterviewState(
            turn_id=0,
            history=[{"role": "system", "content": system_prompt}],
        )

        # Turno 0: chiediamo al modello di presentarsi e iniziare
        user_bootstrap = (
            "Inizia il colloquio: presentati brevemente e chiedi al candidato "
            "di presentarsi."
        )
        turn = self._call_llm(state, user_bootstrap)
        state.last_turn = turn
        return turn, state

    # ------------------------------------------------------------------
    # Turno successivo
    # ------------------------------------------------------------------
    def next_turn(
        self,
        *,
        state: InterviewState,
        candidate_answer: str,
    ) -> HireReadyTurn:
        """Elabora la risposta del candidato e restituisce il turno successivo."""
        if state.is_closed:
            raise RuntimeError("Il colloquio è già concluso.")
        if not candidate_answer.strip():
            raise ValueError("La risposta del candidato è vuota.")

        # Se l'ultimo turno ha posto una domanda, registriamo la risposta
        if state.last_turn and state.last_turn.next_question is not None:
            state.history.append({"role": "user", "content": candidate_answer.strip()})
            state.turn_id += 1

        turn = self._call_llm(state, candidate_answer.strip())
        state.last_turn = turn

        # Chiusura per volgarità o per fine colloquio
        if turn.is_final or turn.is_meaningful.azione == "blocca":
            state.is_closed = True
            if turn.is_meaningful.azione == "blocca":
                # Forziamo il messaggio di cortesia in italiano
                turn = self._force_close_turn(turn)
                state.last_turn = turn

        return turn

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _call_llm(
        self,
        state: InterviewState,
        last_user_message: str,
    ) -> HireReadyTurn:
        # Se l'ultimo messaggio in history è già la risposta utente la riusiamo,
        # altrimenti la accodiamo (turno 0 non ha una risposta utente vera).
        history = list(state.history)
        if not history or history[-1]["content"] != last_user_message:
            history.append({"role": "user", "content": last_user_message})

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "HireReadyTurn",
                "strict": True,
                "schema": HireReadyTurn.model_json_schema(),
            },
        }

        try:
            status_code, body = self._lm_studio.chat_completions(
                self.model, history, response_format
            )
        except LMStudioUnavailableError as error:
            raise RuntimeError(str(error)) from error

        if status_code in (401, 403):
            raise RuntimeError("LM Studio richiede una chiave API valida.")
        if not 200 <= status_code < 300:
            raise RuntimeError(
                f"LM Studio ha restituito HTTP {status_code} durante il colloquio."
            )

        try:
            content = json.loads(body)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise RuntimeError("LM Studio ha restituito una risposta inattesa.") from error
        if not isinstance(content, str):
            raise RuntimeError("Gemma non ha restituito un JSON testuale.")

        try:
            turn = HireReadyTurn.model_validate_json(content)
        except ValidationError as error:
            paths = ", ".join(
                ".".join(str(p) for p in issue["loc"]) or "$"
                for issue in error.errors(include_input=False)
            )
            raise RuntimeError(
                f"Gemma ha restituito un turno non conforme allo schema nei campi: {paths}."
                f"Dettaglio: {error.errors(include_input=True)}\n"
                f"Content grezzo: {content!r}"
            ) from error

        # Aggiorna la history con la domanda posta dal modello (se presente)
        if turn.next_question is not None:
            history.append(
                {"role": "assistant", "content": turn.next_question.text}
            )
        state.history = history
        return turn

    @staticmethod
    def _force_close_turn(turn: HireReadyTurn) -> HireReadyTurn:
        """Sostituisce il turno con un messaggio di chiusura controllato."""
        forced = turn.model_copy(
            update={
                "is_final": True,
                "phase": "finale",
                "next_question": None,
                "evaluation_of_previous_answer": (
                    turn.evaluation_of_previous_answer
                    if turn.evaluation_of_previous_answer is not None
                    else EvaluationOfPreviousAnswer(
                        question_id=turn.turn_id - 1 if turn.turn_id > 0 else 0,
                        score=1.0,
                        pertinenza=1.0,
                        comment="Risposta non conforme alle regole di condotta.",
                    )
                ),
            }
        )
        # La property model_validator accetta solo questo formato (is_final=True + phase finale)
        return forced

    # ------------------------------------------------------------------
    # Utility: messaggio finale da mostrare al candidato
    # ------------------------------------------------------------------
    @staticmethod
    def closing_message(turn: HireReadyTurn) -> str:
        """Restituisce il testo finale che il frontend deve mostrare."""
        if turn.is_meaningful.azione == "blocca":
            return FINAL_MESSAGE
        if turn.is_final:
            return (
                "Grazie per il colloquio. La valutazione finale è disponibile "
                "presso il team di selezione."
            )
        return turn.next_question.text if turn.next_question else ""


# ---------------------------------------------------------------------------
# Helper URL (identico a gemma_cv_parser.py)
# ---------------------------------------------------------------------------
def _lm_studio_root_url() -> str:
    url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234").rstrip("/")
    return url[: -len("/v1")] if url.endswith("/v1") else url