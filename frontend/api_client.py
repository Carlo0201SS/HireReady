import os
import requests


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


api_client = HireReadyApiClient()