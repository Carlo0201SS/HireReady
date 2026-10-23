from typing import Dict, Tuple
import requests
from argparse import ArgumentParser


class LMStudioAPI:
    def __init__(self, url: str, api_key: str):
        self._url: str = url
        self._api_key: str = api_key
        self._endpoints: Dict[str, str] = {
            'chat': '/api/v1/chat',
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

    def chat_with_model(self, model: str, input_msg: str, ctx_len: int, temperature: float) -> Tuple[int, str]:
        r = requests.post(
            self._url+self._endpoints['chat'],
            headers=self._auth_and_content_header,
            json={
                'model': model,
                'input': input_msg,
                'integrations': [],
                'context_length': ctx_len,
                'temperature': temperature,
            }
        )

        return r.status_code, r.text

    def get_list_models(self) -> Tuple[int, str]:
        r = requests.get(
            self._url+self._endpoints['list-models'],
            headers=self._auth_header,
        )

        return r.status_code, r.text

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
