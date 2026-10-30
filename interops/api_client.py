# interops/api_client.py

import os
import requests

from backend.domain.models.interview_model import HireReadyTurn, IsMeaningful, EvaluationOfPreviousAnswer
from backend.domain.models.cv_model import CVParsedProfile
from backend.domain.models.api_model import InterviewResponse





class BackendApiError(RuntimeError):
	pass


class HireReadyApiClient:
	def __init__(self, base_url: str | None = None, timeout: float = 80, api_key: str | None = None) -> None:
		self.base_url = (
			base_url or os.getenv("HIREREADY_API_BASE_URL", "http://127.0.0.1:8000")
		).rstrip("/")
		self.timeout = timeout
		self.api_key = api_key if api_key is not None else os.getenv("HIREREADY_API_KEY", "")

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
			raise BackendApiError(
				"Backend HireReady non raggiungibile. Verifica che FastAPI sia avviato."
			) from error

		if not response.ok:
			try:
				detail = response.json().get("detail", "Richiesta non riuscita.")
			except (ValueError, AttributeError):
				detail = "Richiesta non riuscita."
			raise BackendApiError(str(detail))
		return response.json()

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

	def parse_cv_for_interview(self, anonymized_cv: str, selected_position: str) -> dict:
		return self._request(
			"POST",
			"/api/cv/gemma_parse",
			json={
				"anonymized_cv": anonymized_cv,
				"selected_position": selected_position,
			},
		)

	# ------------------------------------------------------------------
	# Colloquio
	# ------------------------------------------------------------------
	def interview(
		self,
		*,
		history: list[dict[str, str]] | None = None,
		last_turn: HireReadyTurn | None = None,
		candidate_answer: str | None = None,
		selected_position: str | None = None,
		profile: CVParsedProfile | None = None,
	) -> InterviewResponse:
		"""Chiama POST /api/interview.

		- Turno 0: passare `selected_position` + `profile`.
		- Turni successivi: passare `history` + `last_turn` + `candidate_answer`.
		"""
		payload: dict = {"history": history or [], "last_turn": last_turn or None}
		if candidate_answer is not None:
			payload["candidate_answer"] = candidate_answer
		if selected_position is not None:
			payload["selected_position"] = selected_position
		if profile is not None:
			payload["profile"] = profile
		return self._request("POST", "/api/interview", json=payload)

	# ------------------------------------------------------------------
	# Utility
	# ------------------------------------------------------------------
	#@staticmethod
	#def is_interview_closed(turn: dict) -> bool:
	#	"""Determina se un HireReadyTurn chiude il colloquio."""
	#	if not turn:
	#		return False
	#	is_meaningful = turn.get("is_meaningful") or {}
	#	return bool(turn.get("is_final") or is_meaningful.get("azione") == "blocca")


api_client = HireReadyApiClient()