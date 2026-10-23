from typing import Any, Dict, List, Tuple
import requests
from argparse import ArgumentParser


class LMStudioUnavailableError(RuntimeError):
    """LM Studio non raggiungibile (server spento, timeout, errore di rete)."""


class LMStudioAPI:
    def __init__(self, url: str, api_key: str, timeout: float = 120):
        self._url: str = url.rstrip('/')
        self._api_key: str = api_key
        self._timeout: float = timeout
        self._endpoints: Dict[str, str] = {
            'chat': '/api/v1/chat',
            # Endpoint OpenAI-compatibile: l'unico che supporta response_format / json_schema
            'chat-completions': '/v1/chat/completions',
            'list-models': '/api/v1/models',
            'load-model': '/api/v1/models/load',
            'unload-model': '/api/v1/models/unload',
            'download-model': '/api/v1/models/download',
            'get-download-model': '/api/v1/models/download/status',
        }

    @property
    def _auth_header(self) -> Dict[str, str]:
        return {'Authorization': f'Bearer {self._api_key}'}

    @property
    def _auth_and_content_header(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
        }

    def _send(self, method: str, endpoint: str, **kwargs) -> Tuple[int, str]:
        try:
            r = requests.request(
                method,
                self._url + self._endpoints[endpoint],
                timeout=self._timeout,
                **kwargs,
            )
        except requests.RequestException as error:
            raise LMStudioUnavailableError(
                'Impossibile contattare LM Studio. Verifica che il server locale sia avviato.'
            ) from error
        return r.status_code, r.text

    def chat_with_model(self, model: str, input_msg: str, ctx_len: int, temperature: float) -> Tuple[int, str]:
        return self._send(
            'POST',
            'chat',
            headers=self._auth_and_content_header,
            json={
                'model': model,
                'input': input_msg,
                'integrations': [],
                'context_length': ctx_len,
                'temperature': temperature,
            },
        )

    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Dict[str, Any] | None = None,
    ) -> Tuple[int, str]:
        payload: Dict[str, Any] = {'model': model, 'messages': messages}
        if response_format is not None:
            payload['response_format'] = response_format
        return self._send(
            'POST',
            'chat-completions',
            headers=self._auth_and_content_header,
            json=payload,
        )

    def get_list_models(self) -> Tuple[int, str]:
        return self._send('GET', 'list-models', headers=self._auth_header)

    def load_model(self, model_id: str) -> Tuple[int, str]:
        raise NotImplementedError('TBA!')

    def unload_model(self, model_id: str) -> Tuple[int, str]:
        raise NotImplementedError('TBA!')

    def download_model(self, model_id: str) -> Tuple[int, str]:
        raise NotImplementedError('TBA!')

    def get_download_model(self, model_id: str) -> Tuple[int, str]:
        raise NotImplementedError('TBA!')

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('url', help='URL to LM Studio API')
    parser.add_argument('api_key', help='API key')
    args = parser.parse_args()
    api = LMStudioAPI(args.url, args.api_key)

    print(f'Available models: {api.get_list_models()}')
