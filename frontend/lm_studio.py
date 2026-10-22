# backend/lm_studio_client.py
import os
import requests

from dotenv import load_dotenv


load_dotenv()


class LmStudioError(RuntimeError):
    pass


class LmStudioClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 120) -> None:
        self.base_url = base_url or os.getenv("LM_STUDIO_URL","http://127.0.0.1:1234")
        self.api_key = api_key or os.getenv("LM_STUDIO_API_KEY","lm-studio")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def chat(self, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise LmStudioError("LM Studio non raggiungibile.") from error
        if not response.ok:
            raise LmStudioError(f"LM Studio ha risposto {response.status_code}.")
        return response.json()





lm_studio_client = LmStudioClient()