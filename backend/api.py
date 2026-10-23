from functools import lru_cache

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from backend.backend import (
	anonymize_cv,
	extract_cv_text,
	is_anonymization_available,
	parse_cv_for_interview,
)
from backend.domain.models.api import (
	AnonymizationStatusResponse,
	CVParserRequest,
	CVParserResponse,
	CVTextRequest,
	CVTextResponse,
)

from backend.manager.cv.docx_extractor import DocxExtractor
from backend.manager.cv.pymupdf_extractor import PyMuPDFExtractor
from backend.manager.cv.rizzo_anonymizer import RizzoAnonymizer

from backend.application.anonymization_service import AnonymizationService
from backend.application.cv_extraction_service import CVExtractionService


app = FastAPI(title="HireReady API", version="1.0.0")


# ---Per ottenere i servizi: ---------------------------------------------------

@lru_cache(maxsize=1) # mantiene in cache elementi già caricati per evitare un nuovo scaricamento
def get_anonymization_service() -> AnonymizationService:
    return AnonymizationService(RizzoAnonymizer())


@lru_cache(maxsize=1)
def get_cv_extraction_service() -> CVExtractionService:
    return CVExtractionService(PyMuPDFExtractor(), DocxExtractor())


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
def anonymization_status(
    service: AnonymizationService = Depends(get_anonymization_service),
) -> AnonymizationStatusResponse:
    return AnonymizationStatusResponse(available=service.is_available)


@app.post("/api/cv/extract", response_model=CVTextResponse)
async def extract_cv(file: UploadFile = File(...), service: CVExtractionService = Depends(get_cv_extraction_service),
) -> CVTextResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Il file deve avere un nome valido.")

    try:
        content = await file.read()
        text = service.extract_text(file.filename, content)
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