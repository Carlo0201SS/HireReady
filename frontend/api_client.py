from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import requests
from fastapi import HTTPException

if TYPE_CHECKING:
	from backend.domain.models.cv_model import CVParsedProfile
	from backend.domain.models.interview_model import HireReadyTurn


class HireReadyApiClient:
	def __init__(self, base_url: str | None = None, timeout: float = 120, api_key: str | None = None) -> None:
		self.base_url = (
			base_url or os.getenv("HIREREADY_API_BASE_URL", "http://127.0.0.1:8000")
		).rstrip("/")
		self.timeout = timeout
		self.api_key = api_key if api_key is not None else os.getenv("HIREREADY_API_KEY", "")

	@staticmethod
	def _raise_for_http_error(response: requests.Response) -> None:
		status_code = response.status_code
		if 300 <= status_code < 400:
			category = "Reindirizzamento HTTP"
		elif 400 <= status_code < 500:
			category = "Errore client HTTP"
		elif 500 <= status_code < 600:
			category = "Errore server HTTP"
		elif not 200 <= status_code < 300:
			raise HTTPException(
				status_code=502,
				detail=f"Status HTTP inatteso {status_code}: {response.text or response.reason}",
			)
		else:
			return

		try:
			error_body = response.json()
		except ValueError as error:
			detail = response.text or f"{type(error).__name__}: {error}"
		else:
			if isinstance(error_body, dict):
				detail = error_body.get("detail", response.text or response.reason)
			else:
				detail = response.text or response.reason
		raise HTTPException(
			status_code=status_code,
			detail=f"{category} {status_code}: {detail}",
		)

	def _request(self, method: str, path: str, **kwargs) -> dict:
		headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
		try:
			response = requests.request(
				method,
				f"{self.base_url}{path}",
				timeout=self.timeout,
				headers=headers,
				**kwargs,
			)
		except requests.RequestException as error:
			raise HTTPException(
				status_code=503,
				detail=f"{type(error).__name__}: {error}",
			) from error
		except Exception as error:
			raise HTTPException(
				status_code=500,
				detail=f"{type(error).__name__}: {error}",
			) from error

		self._raise_for_http_error(response)
		try:
			return response.json()
		except Exception as error:
			raise HTTPException(
				status_code=502,
				detail=f"{type(error).__name__}: {error}",
			) from error

	# ------------------------------------------------------------------
	# CV
	# ------------------------------------------------------------------
	def extract_cv_text(self, filename: str, content: bytes) -> str:
		result = self._request(
			"POST",
			"/api/cv/extract",
			files={"file": (filename, content)},
		)
		return result["text"]

	def anonymization_status(self) -> dict:
		return self._request("GET", "/api/anonymization/status")

	def anonymization_available(self) -> bool:
		return self.anonymization_status()["available"]

	def anonymize_cv(self, text: str) -> str:
		result = self._request("POST", "/api/cv/anonymize", json={"text": text})
		return result["text"]

	def parse_cv_for_interview(
		self,
		anonymized_cv: str,
		selected_position: str,
		position_description: str = "",
	) -> dict:
		payload = {
			"anonymized_cv": anonymized_cv,
			"selected_position": selected_position,
		}
		if position_description.strip():
			payload["position_description"] = position_description
		return self._request(
			"POST",
			"/api/cv/gemma_parse",
			json=payload,
		)

	# ------------------------------------------------------------------
	# Colloquio
	# ------------------------------------------------------------------
	def interview(
		self,
		*,
		anonymized_cv: str,
		history: list[dict[str, str]] | None = None,
		last_turn: HireReadyTurn | dict | None = None,
		candidate_answer: str | None = None,
		selected_position: str | None = None,
		level_position: str | None = None,
		position_description: str | None = None,
		profile: CVParsedProfile | dict | None = None,
	) -> dict:
		"""Chiama POST /api/interview.

		- Tutti i turni: passare il CV anonimizzato.
		- Turno 0: passare `selected_position` + `profile`.
		- Turni successivi: passare `history` + `last_turn` + `candidate_answer`.
		"""
		# requests non serializza Pydantic: normalizziamo a dict prima di inviare.
		last_turn_payload = (
			last_turn.model_dump()
			if last_turn is not None and not isinstance(last_turn, dict)
			else last_turn
		)
		profile_payload = (
			profile.model_dump()
			if profile is not None and not isinstance(profile, dict)
			else profile
		)

		payload: dict = {
			"history": history or [],
			"anonymized_cv": anonymized_cv,
			"last_turn": last_turn_payload,
		}
		if candidate_answer is not None:
			payload["candidate_answer"] = candidate_answer
		if selected_position is not None:
			payload["selected_position"] = selected_position
		if level_position is not None:
			payload["level_position"] = level_position
		if position_description is not None and position_description.strip():
			payload["position_description"] = position_description
		if profile_payload is not None:
			payload["profile"] = profile_payload
		return self._request("POST", "/api/interview", json=payload)

	def generate_report(
		self,
		*,
		history: list[dict[str, str]] | None = None,
		contenuto: str = "",
		answers: list[dict[str, Any]] | None = None,
		score: float | None = None,
	) -> dict:
		return self._request(
			"POST",
			"/api/report",
			json={
				"history": history or [],
				"contenuto": contenuto,
				"answers": answers or [],
				"score": score,
			},
		)

	def download_report_pdf(self, report: dict[str, Any]) -> bytes:
		headers = {"Authorization": "******"} if self.api_key else {}
		try:
			response = requests.request(
				"POST",
				f"{self.base_url}/api/report/pdf",
				timeout=self.timeout,
				headers=headers,
				json=report,
			)
		except requests.RequestException as error:
			raise HTTPException(
				status_code=503,
				detail=f"{type(error).__name__}: {error}",
			) from error
		except Exception as error:
			raise HTTPException(
				status_code=500,
				detail=f"{type(error).__name__}: {error}",
			) from error

		self._raise_for_http_error(response)
		return response.content

	# ------------------------------------------------------------------
	# Utility
	# ------------------------------------------------------------------
	@staticmethod
	def is_interview_closed(turn: dict) -> bool:
		"""Determina se un HireReadyTurn chiude il colloquio."""
		if not turn:
			return False
		is_meaningful = turn.get("is_meaningful") or {}
		language = str(is_meaningful.get("lingua", "")).strip().casefold()
		return bool(
			turn.get("is_final")
			or is_meaningful.get("azione") == "blocca"
			or language != "italiano"
		)

	@staticmethod
	def is_final_turn(turn: dict | None) -> bool:
		return bool(
			turn
			and turn.get("phase") == "finale"
			and turn.get("is_final") is True
			and turn.get("closure_reason") is None
		)

	@staticmethod
	def turn_message(turn: dict | None) -> str:
		"""Testo da mostrare per un HireReadyTurn serializzato.

		- Blocco per linguaggio inappropriato → messaggio + motivazione.
		- Turno finale → messaggio di chiusura cortese.
		- Turno normale → `next_question.text`.
		- Nessun turno → messaggio di attesa.
		"""
		if not turn:
			return "In attesa dell'inizio del colloquio…"

		is_meaningful = turn.get("is_meaningful") or {}
		if is_meaningful.get("azione") == "blocca":
			return (
				"Il colloquio è terminato.\n\n"
				f"Motivo: {is_meaningful.get('motivazione', 'motivo non specificato')}"
			)

		if turn.get("closure_reason") == "profile_contradiction":
			return (
				"Il colloquio è stato interrotto perché sono emerse informazioni "
				"incompatibili tra il profilo e le risposte. Sarà necessaria una verifica."
			)

		if HireReadyApiClient.is_final_turn(turn):
			return "Grazie per aver partecipato al colloquio!"

		next_question = turn.get("next_question")
		if next_question and next_question.get("text"):
			return next_question["text"]

		return "In attesa della prossima domanda…"


api_client = HireReadyApiClient()