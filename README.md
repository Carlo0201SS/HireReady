# HireReady

## Installazione e avvio

1. **Prepara l'ambiente.** Installa Python 3.12 o successivo e, facoltativamente, [uv](https://docs.astral.sh/uv/). Apri PowerShell nella cartella del progetto.

2. **Installa le dipendenze.** Con uv:

   ```powershell
   uv sync
   ```

   In alternativa, crea un ambiente virtuale e installa i pacchetti con pip:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. **Prepara il modello linguistico.** Installa LM Studio, scarica un modello chat compatibile e avvia il server locale. HireReady usa per impostazione predefinita `http://127.0.0.1:1234` e il modello per la quale HireReady è stato configurato e messo a punto è `google/gemma-4-e2b`; se necessario configura `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL` e `LM_STUDIO_API_KEY` nell'ambiente del backend.

4. **Avvia il backend.** In un terminale PowerShell, dalla cartella del progetto:

   ```powershell
   $env:HIREREADY_FINAL_TURN_ID = "11"
   uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
   ```

   Se hai installato le dipendenze con pip, attiva prima l'ambiente virtuale e sostituisci `uv run uvicorn` con `python -m uvicorn`. Al primo avvio il backend scarica e prepara automaticamente il modello locale di anonimizzazione; è necessaria una connessione Internet e il download può richiedere tempo.

5. **Avvia l'interfaccia.** In un secondo terminale, dalla cartella del progetto:

   ```powershell
   uv run streamlit run frontend/app.py
   ```

   Con pip, attiva l'ambiente virtuale e usa `streamlit run frontend/app.py`. Apri nel browser l'indirizzo locale mostrato da Streamlit.

## Funzionamento

HireReady aiuta a prepararsi a un colloquio di lavoro: estrae e analizza il CV, adatta le domande alla posizione e conduce un'intervista guidata. Le risposte vengono valutate e confrontate con le informazioni del CV per evidenziare eventuali incoerenze; al termine viene preparato un riepilogo con risultati e suggerimenti, scaricabile anche in PDF.
