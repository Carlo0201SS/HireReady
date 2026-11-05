# HireReady
.

## Avvio

Backend e frontend si avviano in due terminali dalla cartella radice del progetto.

Terminale backend:

```powershell
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminale frontend:

```powershell
streamlit run frontend/app.py
```

Per cambiare l'indirizzo del backend nel frontend, imposta `HIREREADY_API_BASE_URL`. La documentazione interattiva degli endpoint FastAPI e' disponibile su `http://127.0.0.1:8000/docs`.

Gli endpoint correnti sono `GET /api/health`, `GET /api/anonymization/status`, `POST /api/cv/extract`, `POST /api/cv/anonymize`, `POST /api/cv/gemma_parse`, `POST /api/interview` e `POST /api/report`.

`POST /api/cv/gemma_parse` riceve `anonymized_cv` e `selected_position`, quindi restituisce `selected_position` e un profilo strutturato (`professional_summary`, `technical_skills`, `relevant_experience`, `education`, `certifications`, `interview_focus`). La UI conserva il risultato in `st.session_state` per i passaggi futuri; in questa fase non viene generata una chat né scritto un record su database.

Al termine del colloquio, `POST /api/report` riceve la cronologia (`history`), la motivazione conclusiva (`contenuto`) e le risposte valutate (`answers`, con domanda, risposta, motivazione e punteggio da 1 a 10). Il riepilogo è generato da Gemma; la pagina Report mostra il riepilogo e il dettaglio di ogni risposta.

Il frontend avvia l'anonimizzazione in background dopo l'estrazione del CV. L'utente può scegliere la posizione mentre il modello lavora; l'analisi del CV per la posizione selezionata attende il completamento dell'anonimizzazione.

## Modello di anonimizzazione (Rizzo PII)

All'avvio il backend scarica in background il modello `rizzoaiacademy/rizzo-pii-0.3B` in `ai_models/` (circa 1,2 GB, solo la prima volta) e lo carica in memoria. Lo stato è visibile su `GET /api/anonymization/status` (`downloading`, `loading`, `ready`, `error`). Per disattivare il precaricamento (es. nei test) imposta `HIREREADY_PRELOAD_MODELS=0`. Download manuale: `python -m backend.manager.cv.rizzo_anonymizer --force`.

La cartella `ai_models/` è esclusa da git: i pesi non vanno committati.
