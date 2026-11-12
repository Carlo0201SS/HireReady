# HireReady
.

## Avvio

Backend e frontend si avviano in due terminali dalla cartella radice del progetto.

Terminale backend:

```powershell
$env:HIREREADY_FINAL_TURN_ID = "11"
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminale frontend:

```powershell
streamlit run frontend/app.py
```

Per cambiare l'indirizzo del backend nel frontend, imposta `HIREREADY_API_BASE_URL`. La documentazione interattiva degli endpoint FastAPI e' disponibile su `http://127.0.0.1:8000/docs`.

`HIREREADY_FINAL_TURN_ID` controlla il turno di chiusura del colloquio (default `11`, minimo `5`). Impostalo prima di avviare il backend; il valore `11` mantiene il flusso standard di 3 turni CV, 1 di presentazione e 7 tecnici.

Gli endpoint correnti sono `GET /api/health`, `GET /api/anonymization/status`, `POST /api/cv/extract`, `POST /api/cv/anonymize`, `POST /api/cv/gemma_parse`, `POST /api/interview`, `POST /api/report` e `POST /api/report/pdf`.

`POST /api/cv/gemma_parse` riceve `anonymized_cv` e `selected_position`, quindi restituisce `selected_position` e un profilo strutturato (`professional_summary`, `technical_skills`, `relevant_experience`, `education`, `certifications`, `interview_focus`). La UI conserva il risultato in `st.session_state` per i passaggi futuri; in questa fase non viene generata una chat né scritto un record su database.

Al termine del colloquio, `POST /api/report` riceve la cronologia (`history`), la motivazione conclusiva (`contenuto`) e le risposte valutate (`answers`, con domanda, risposta, motivazione e punteggio da 1 a 10). Il riepilogo è generato da Gemma; la pagina Report mostra il riepilogo e il dettaglio di ogni risposta. Se una risposta contiene anni espliciti confrontabili con il profilo o con risposte precedenti, un controllo dedicato verifica le cronologie lavorative. Il colloquio viene interrotto per contraddizione solo se il verificatore trova due citazioni letterali incompatibili; informazioni mancanti o ambigue sono classificate come non verificabili. `POST /api/report/pdf` riceve il report generato e restituisce il PDF pronto per il download usando ReportLab, senza dipendenze native GTK/Pango su Windows.

Il frontend avvia l'anonimizzazione in background dopo l'estrazione del CV. L'utente può scegliere la posizione mentre il modello lavora; l'analisi del CV per la posizione selezionata attende il completamento dell'anonimizzazione.

## Modello di anonimizzazione (Rizzo PII)

All'avvio il backend scarica in background il modello `rizzoaiacademy/rizzo-pii-0.3B` in `ai_models/` (circa 1,2 GB, solo la prima volta) e lo carica in memoria. Lo stato è visibile su `GET /api/anonymization/status` (`downloading`, `loading`, `ready`, `error`). Il nome e cognome vengono mantenuti nel CV anonimizzato; gli altri dati personali rilevati continuano a essere censurati. Per disattivare il precaricamento (es. nei test) imposta `HIREREADY_PRELOAD_MODELS=0`. Download manuale: `python -m backend.manager.cv.rizzo_anonymizer --force`.

La cartella `ai_models/` è esclusa da git: i pesi non vanno committati.
