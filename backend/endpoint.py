from contextlib import asynccontextmanager
import os
import threading

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.controller import (
	anonymization_state,
	anonymize_cv,
	extract_cv_text,
	is_anonymization_available,
	parse_cv_for_interview,
	warm_up_anonymization,
)
from backend.domain.models.api_model import (
	AnonymizationStatusResponse,
	CVParserRequest,
	CVParserResponse,
	CVTextRequest,
	CVTextResponse,
)






@asynccontextmanager
async def lifespan(_: FastAPI):
	# All'avvio scarica (se manca) e carica il modello Rizzo PII in background:
	# l'API risponde subito e /api/anonymization/status ne riporta lo stato.
	if os.getenv("HIREREADY_PRELOAD_MODELS", "1") == "1":
		threading.Thread(target=warm_up_anonymization, name="rizzo-warm-up", daemon=True).start()
	yield


app = FastAPI(title="HireReady API", version="1.0.0", lifespan=lifespan)



# ---Endpoint-----------------------------------------------------------------

@app.get("/")
def root() -> dict[str, object]:
	return {
		"service": "HireReady API",
		"status": "ok",
		"documentation": "/docs",
		"health": "/api/health",
		"endpoints": {
			"anonymization_status": "GET /api/anonymization/status",
			"cv_extraction": "POST /api/cv/extract",
			"cv_anonymization": "POST /api/cv/anonymize",
			"cv_interview_parsing": "POST /api/cv/gemma_parse",
		},
	}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/anonymization/status", response_model=AnonymizationStatusResponse)
def anonymization_status() -> AnonymizationStatusResponse:
    return AnonymizationStatusResponse(
        available=is_anonymization_available(),
        state=anonymization_state(),
    )


@app.post("/api/cv/extract", response_model=CVTextResponse)
async def extract_cv(file: UploadFile = File(...)) -> CVTextResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Il file deve avere un nome valido.")

    try:
        content = await file.read()
        text = extract_cv_text(file.filename, content)
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail="Impossibile estrarre il testo dal documento caricato.",
        ) from error
    finally:
        await file.close()

    return CVTextResponse(text=text)


@app.post("/api/cv/anonymize", response_model=CVTextResponse)
def anonymize_cv_text(request: CVTextRequest) -> CVTextResponse:
	try:
		return CVTextResponse(text=anonymize_cv(request.text))
	except FileNotFoundError as error:
		raise HTTPException(
			status_code=503,
			detail="Il modello locale di anonimizzazione non è disponibile.",
		) from error
	except Exception as error:
		raise HTTPException(
			status_code=500,
			detail="Anonimizzazione non riuscita.",
		) from error


@app.post("/api/cv/gemma_parse", response_model=CVParserResponse)
def parse_cv_for_interview_endpoint(request: CVParserRequest) -> CVParserResponse:
	try:
		return parse_cv_for_interview(
			anonymized_cv=request.anonymized_cv,
			selected_position=request.selected_position,
		)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	except RuntimeError as error:
		raise HTTPException(status_code=502, detail=str(error)) from error


