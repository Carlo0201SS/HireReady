from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.backend import anonymize_cv, extract_cv_text, is_anonymization_available
from backend.domain.models.api import (
	AnonymizationStatusResponse,
	CVTextRequest,
	CVTextResponse,
)


app = FastAPI(title="HireReady API", version="1.0.0")


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
		},
	}


@app.get("/api/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/api/anonymization/status", response_model=AnonymizationStatusResponse)
def anonymization_status() -> AnonymizationStatusResponse:
	return AnonymizationStatusResponse(available=is_anonymization_available())


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