import io
import logging
import os
import threading
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)



class STTManager:
    """
    Manager per la trascrizione vocale (Speech-to-Text) basata su faster-whisper.
    Mantiene un'istanza del modello persistente per evitare ricaricamenti.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ):
        """
        Inizializza il motore STT.

        Args:
            model_size: Dimensione modello Whisper ('tiny', 'base', 'small', 'medium', 'large').
            device: 'cpu' o 'cuda'.
            compute_type: 'int8', 'float16', 'float32' (int8 è ottimo per CPU).
            cpu_threads: Numero di thread CPU per la trascrizione.
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self._model = None
        self._ready = threading.Event()
        self._error: Optional[str] = None

    def warm_up(self) -> None:
        """
        Carica il modello in memoria. Blocca finché il modello non è pronto.
        Utile da chiamare in un thread separato all'avvio del server.
        """
        if self._model is not None:
            return

        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
        except Exception as error:
            # Senza questo l'eccezione si perde nel thread di warm-up
            # e la UI resta per sempre in "si sta avviando".
            self._error = f"{type(error).__name__}: {error}"
            logger.exception("Caricamento modello STT non riuscito.")
            return
        self._error = None
        self._ready.set()

    @property
    def state(self) -> str:
        """'error', 'ready' oppure 'loading'."""
        if self._error:
            return "error"
        return "ready" if self._ready.is_set() else "loading"

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def is_ready(self) -> bool:
        """True se il modello è caricato e pronto per la trascrizione."""
        return self._ready.is_set()

    def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        initial_prompt: Optional[str] = None,
    ) -> dict:
        """
        Trascrive l'audio e restituisce il testo con metadati.

        Args:
            audio_bytes: Byte del file audio (WAV, MP3, ecc.).
            language: Codice lingua ('it', 'en', ...). None per auto-detect.
            beam_size: Ampiezza beam search (5 è un buon compromesso).
            vad_filter: Se True, rimuove i silenzi prima della trascrizione.
            initial_prompt: Testo di contesto (ruolo, termini tecnici) che orienta
                il vocabolario di Whisper. Non viene trascritto.

        Returns:
            Dict con 'text', 'language', 'language_probability', 'segments'.
        """
        if not self.is_ready:
            raise RuntimeError("Modello STT non ancora pronto. Chiamare warm_up() prima.")

        audio_file = io.BytesIO(audio_bytes)
        segments, info = self._model.transcribe(
            audio_file,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            initial_prompt=initial_prompt or None,
        )

        # I segmenti sono un generatore: li materializziamo
        segment_list = []
        text_parts = []
        for seg in segments:
            segment_list.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })
            text_parts.append(seg.text.strip())

        return {
            "text": " ".join(text_parts).strip(),
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": segment_list,
        }

    def transcribe_to_text(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> str:
        """
        Versione semplificata: restituisce solo il testo trascritto.
        """
        result = self.transcribe(audio_bytes, language=language)
        return result["text"]

    def close(self) -> None:
        """Rilascia le risorse del modello."""
        self._model = None
        self._ready.clear()