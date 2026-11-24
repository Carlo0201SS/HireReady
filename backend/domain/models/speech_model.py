from fastapi import UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from pydantic import BaseModel, Field
from typing import List, Optional

# Questo non è un modello Pydantic per il body, ma definisce i parametri del form
# Puoi usarlo come riferimento per la documentazione, ma la dichiarazione avviene nell'endpoint
class TranscribeRequest(BaseModel):
    language: Optional[str] = None
    beam_size: int = 5

class TranscriptionSegment(BaseModel):
    start: float = Field(..., description="Tempo di inizio del segmento in secondi")
    end: float = Field(..., description="Tempo di fine del segmento in secondi")
    text: str = Field(..., description="Testo trascritto nel segmento")

class TranscribeResponse(BaseModel):
    text: str = Field(..., description="Testo completo trascritto")
    language: str = Field(..., description="Codice lingua rilevato (es. 'it')")
    language_probability: float = Field(..., description="Confidenza del rilevamento lingua")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="Dettaglio dei singoli segmenti")