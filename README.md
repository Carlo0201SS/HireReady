# HireReady
.

## Colloquio locale con Gemma

Il primo turno usa esclusivamente il testo anonimizzato del CV e invia la richiesta a LM Studio tramite la sua API compatibile con OpenAI.

1. Scarica `google/gemma-4-e2b` in LM Studio e caricalo.
2. In LM Studio avvia il server locale dalla sezione Developer/API Server, sulla porta `1234`.
3. Avvia HireReady con `streamlit run frontend/app.py`.
4. Carica e anonimizza un CV, poi seleziona **Avvia colloquio con questo CV**.

L'endpoint predefinito e' `http://127.0.0.1:1234/v1`. Se LM Studio richiede autenticazione, imposta la chiave nel terminale prima di avviare Streamlit:

```powershell
$env:LM_STUDIO_API_KEY = "<chiave API locale>"
streamlit run frontend/app.py
```

Il modello predefinito e' `google/gemma-4-e2b`; endpoint e identificativo possono essere sovrascritti con `LM_STUDIO_BASE_URL` e `LM_STUDIO_MODEL`.
