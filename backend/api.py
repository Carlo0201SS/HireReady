from contextlib import asynccontextmanager
import logging
import os
import threading
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile

from backend.controller import (
	anonymization_state,
	anonymize_cv,
	extract_cv_text,
	generate_interview_report,
	generate_report_pdf,
	interview_handle,
	is_anonymization_available,
	is_stt_available,
	parse_cv_for_interview,
	save_report_pdf,
	stt_state,
	transcribe_audio,
	warm_up_anonymization,
	warm_up_stt,
)
from backend.domain.models.api_model import (
	AnonymizationStatusResponse,
	CVParserRequest,
	CVParserResponse,
	CVTextRequest,
	CVTextResponse,
	InterviewResponse,
	InterviewRequest,
)
from backend.domain.models.report_model import (
	InterviewReportRequest,
	InterviewReportResponse,
)
from backend.domain.models.interview_model import (
	HireReadyTurn,
)
from backend.domain.models.speech_model import (
  # se vuoi un modello dedicato, vedi sotto
	TranscribeResponse,
)
from backend.manager.report.reportlab_pdf_renderer import ReportPdfRendererUnavailable


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Avvio warm-up modelli in background (come per Rizzo)
    if os.getenv("HIREREADY_PRELOAD_MODELS", "1") == "1":
        threading.Thread(
            target=warm_up_anonymization,
            name="rizzo-warm-up",
            daemon=True,
        ).start()
        threading.Thread(
            target=warm_up_stt,
            name="stt-warm-up",
            daemon=True,
        ).start()
    yield
    # Cleanup allo shutdown: libera la memoria del modello STT
    # (il riferimento vive nel controller, non qui)
    # Se vuoi un cleanup esplicito, esponi una funzione close_stt() dal controller.


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
			"interview_report": "POST /api/report",
			"interview_report_pdf": "POST /api/report/pdf",
			"interview": "POST /api/interview",
			"stt_status": "GET /api/stt/status",
			"stt_transcribe": "POST /api/stt/transcribe",
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
        logger.exception("Impossibile estrarre il testo dal documento caricato.")
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
			position_description=request.position_description,
		)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	except RuntimeError as error:
		raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/interview", response_model=InterviewResponse)
def interview(request: InterviewRequest) -> InterviewResponse:
	try:
		turn, state = interview_handle(
			history=request.history,
			anonymized_cv=request.anonymized_cv,
			last_turn=request.last_turn,
			candidate_answer=request.candidate_answer,
			selected_position=request.selected_position,
			level_position=request.level_position,
			position_description=request.position_description,
			profile=request.profile,
		)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	except RuntimeError as error:
		raise HTTPException(status_code=502, detail=str(error)) from error
	except Exception as error:
		logger.exception("Errore inatteso in /api/interview")
		raise HTTPException(
			status_code=500, detail=f"Errore interno: {type(error).__name__}: {error}"
		) from error
	return InterviewResponse(turn=turn, history=state.history, is_closed=state.is_closed)


@app.post("/api/report", response_model=InterviewReportResponse)
def interview_report(request: InterviewReportRequest) -> InterviewReportResponse:
	try:
		return generate_interview_report(request)
	except RuntimeError as error:
		raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/report/pdf")
def interview_report_pdf(request: InterviewReportResponse) -> Response:
	try:
		pdf = generate_report_pdf(request)
		filename = save_report_pdf(pdf)
	except ReportPdfRendererUnavailable as error:
		logger.exception("Renderer PDF non disponibile.")
		raise HTTPException(status_code=503, detail=str(error)) from error
	except Exception as error:
		logger.exception("Impossibile generare il PDF del report.")
		raise HTTPException(
			status_code=500,
			detail="Impossibile generare il PDF del report.",
		) from error
	return Response(
		content=pdf,
		media_type="application/pdf",
		headers={"Content-Disposition": f'attachment; filename="{filename}"'},
	)


@app.get("/api/stt/status")
def stt_status_endpoint() -> dict[str, object]:
	return {
		"available": is_stt_available(),
	}


@app.post("/api/stt/transcribe", response_model=TranscribeResponse)
async def stt_transcribe(
	audio: UploadFile = File(...),
	language: Optional[str] = Form(None),
	prompt: Optional[str] = Form(None),
) -> TranscribeResponse:
	if not is_stt_available():
		raise HTTPException(status_code=503, detail="Modello STT non ancora pronto")

	try:
		audio_bytes = await audio.read()
		if not audio_bytes:
			raise HTTPException(status_code=400, detail="Il file audio è vuoto.")
		result = transcribe_audio(
			audio_bytes,
			language=language,
			initial_prompt=prompt,
		)
	except HTTPException:
		raise
	except Exception as error:
		logger.exception("Trascrizione audio non riuscita.")
		raise HTTPException(
			status_code=500,
			detail=f"Trascrizione audio non riuscita: {type(error).__name__}: {error}",
		) from error
	finally:
		await audio.close()

	return TranscribeResponse(**result)