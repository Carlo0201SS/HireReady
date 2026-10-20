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

Gli endpoint correnti sono `GET /api/health`, `GET /api/anonymization/status`, `POST /api/cv/extract`, `POST /api/cv/anonymize` e `POST /api/cv/gemma_parse`.

`POST /api/cv/gemma_parse` riceve `anonymized_cv` e `selected_position`, quindi restituisce `selected_position` e un profilo strutturato (`professional_summary`, `technical_skills`, `relevant_experience`, `education`, `certifications`, `interview_focus`). La UI conserva il risultato in `st.session_state` per i passaggi futuri; in questa fase non viene generata una chat né scritto un record su database.
