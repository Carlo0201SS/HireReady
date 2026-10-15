# Valutazione `rizzo-pii-0.3B` — **v1.5.0** vs **main**

Confronto testa a testa tra il branch `v1.5.0` e il branch `main` di
`rizzoaiacademy/rizzo-pii-0.3B` (mmBERT-base, token classification su 22 tag PII,
45 label BIO).

Entrambi i modelli sono stati scaricati da HF e valutati **con lo stesso script, sugli stessi
file, nella stessa sessione** (8 agosto 2026, 15:28–16:06).

---

## TL;DR

| dataset | righe | entità | micro-F1 v1.5.0 | micro-F1 main | Δ |
|---|---:|---:|---:|---:|---:|
| **validation_real** (held-out reale, IT) | 7.000 | 15.474 | **0.9887** | 0.9886 | +0.0001 |
| **validation_clean** (in-distribution) | 29.297 | 971.204 | **0.9999** | 0.7778 | +0.2221 |
| validation_union (in-distribution, troncato) | 36.297 | 981.459 | **0.9997** | 0.7798 | +0.2199 |

Le due letture vanno tenute separate, e la seconda **non** va riportata come "22 punti di
miglioramento": vedi [Come leggere questi numeri](#come-leggere-questi-numeri).

---

## 1. `validation_real` — il confronto ad armi pari

7.000 righe italiane held-out (Ai4Privacy val IT + DeepMount test + i 5 tag legali IT-only
iniettati in frasi reali della validation). Nessun troncamento a max_len 768.

| | v1.5.0 | main | Δ |
|---|---:|---:|---:|
| micro-F1 | **0.9887** | 0.9886 | +0.0001 |
| micro precision | 0.9875 | 0.9874 | +0.0001 |
| micro recall | 0.9899 | 0.9898 | +0.0001 |
| macro-F1 | 0.9869 | **0.9871** | −0.0002 |
| token accuracy | 0.9984 | 0.9985 | −0.0001 |

**I due modelli sono equivalenti.** Nessun tag si sposta più di ±0.007 e i movimenti stanno
tutti su support piccoli, dentro il rumore.

| TAG | support | F1 v1.5.0 | F1 main | ΔF1 |
|---|---:|---:|---:|---:|
| FULLNAME | 4.390 | 0.9903 | 0.9895 | +0.0008 |
| CATASTO | 1.200 | 1.0000 | 1.0000 | +0.0000 |
| CITY | 953 | 0.9621 | 0.9623 | −0.0001 |
| DATE | 922 | 1.0000 | 1.0000 | +0.0000 |
| TELEPHONENUM | 874 | 1.0000 | 1.0000 | +0.0000 |
| ID_DOC | 800 | 0.9988 | 1.0000 | −0.0012 |
| EMAIL | 748 | 0.9980 | 0.9987 | −0.0007 |
| TIME | 637 | 0.9906 | 0.9914 | −0.0008 |
| STREET | 617 | 0.9588 | 0.9599 | −0.0010 |
| BUILDINGNUM | 594 | 0.9655 | 0.9636 | +0.0019 |
| PIVA | 514 | 1.0000 | 1.0000 | +0.0000 |
| GENDER | 472 | 0.9968 | 1.0000 | −0.0032 |
| PROVINCE | 400 | 0.9987 | 1.0000 | −0.0013 |
| DOCID | 400 | 1.0000 | 1.0000 | +0.0000 |
| CF | 400 | 1.0000 | 1.0000 | +0.0000 |
| AGE | 385 | 0.9781 | 0.9779 | +0.0002 |
| ZIPCODE | 299 | 0.9516 | 0.9522 | −0.0006 |
| IBAN | 278 | 0.9964 | 0.9964 | +0.0000 |
| CREDITCARDNUMBER | 257 | 0.9504 | 0.9452 | +0.0052 |
| AMOUNT | 146 | 0.9897 | 0.9966 | −0.0069 |
| ORG | 145 | 0.9864 | 0.9831 | +0.0033 |
| TARGA | 43 | 1.0000 | 1.0000 | +0.0000 |
| **MICRO** | **15.474** | **0.9887** | **0.9886** | **+0.0001** |
| MACRO | | 0.9869 | 0.9871 | −0.0002 |

### 1.1 Vista relaxed / masking

Metrica più vicina all'uso reale (anonimizzazione): conta i **token di PII che resterebbero in
chiaro**, indipendentemente dal fatto che il confine di entità sia esatto.

| | v1.5.0 | main |
|---|---:|---:|
| F1 relaxed (micro) | 0.9913 | 0.9914 |
| copertura di mascheramento | **99.89%** | 99.87% |
| **token PII lasciati in chiaro** | **60** / 54.093 | 72 / 54.093 |
| over-masking (testo oscurato in più) | 0.22% | 0.18% |

È **l'unica differenza difendibile del confronto**: v1.5.0 lascia scoperti 12 token di PII in
meno, pagandoli con un filo di over-masking. Dove finiscono i token in chiaro di v1.5.0:
FULLNAME 25, CREDITCARDNUMBER 8, CITY 6, TIME 6, AGE 4, STREET 3, BUILDINGNUM 3, il resto ≤ 1.

---

## 2. `validation_clean` — la validation grande

29.297 righe, **971.204 entità**, max_len 1152, **zero righe troncate** → misura completa
(a differenza di `validation_union`, vedi §3).

| | v1.5.0 | main |
|---|---:|---:|
| micro-F1 | **0.99990** | 0.7778 |
| micro precision | 0.99988 | 0.7533 |
| micro recall | 0.99991 | 0.8039 |
| macro-F1 | **0.99990** | 0.7423 |
| token accuracy | 0.99995 | 0.9160 |

**v1.5.0**: 21 tag su 22 stanno ≥ 0.9998 e 15 sono esattamente 1.0000. L'unico tag che non
tocca il muro è **ORG a 0.9982** (P 0.9980 / R 0.9984); seguono CATASTO 0.9999, IBAN 0.9998,
FULLNAME 0.99988.

Per-tag, ordinato per distacco, con gli errori di `main` in valore assoluto:

| TAG | support | F1 v1.5.0 | F1 main | ΔF1 | entità perse (main) | falsi positivi (main) |
|---|---:|---:|---:|---:|---:|---:|
| AMOUNT | 53.503 | 1.0000 | 0.2133 | +0.7866 | 39.529 | 63.528 |
| DOCID | 42.416 | 1.0000 | 0.2812 | +0.7188 | 27.499 | 48.765 |
| TIME | 25.018 | 1.0000 | 0.3407 | +0.6593 | 17.591 | 11.158 |
| CREDITCARDNUMBER | 15.964 | 1.0000 | 0.4192 | +0.5808 | 11.004 | 2.740 |
| GENDER | 27.993 | 1.0000 | 0.5084 | +0.4916 | 18.320 | 388 |
| EMAIL | 64.885 | 1.0000 | 0.6385 | +0.3615 | 21.014 | 28.656 |
| ID_DOC | 17.279 | 1.0000 | 0.6459 | +0.3541 | 6.302 | 5.735 |
| ORG | 38.997 | 0.9982 | 0.6717 | +0.3266 | 2.212 | 33.754 |
| AGE | 22.403 | 1.0000 | 0.7113 | +0.2887 | 6.472 | 6.461 |
| CATASTO | 43.788 | 0.9999 | 0.7470 | +0.2529 | 7.668 | 16.798 |
| PIVA | 18.695 | 1.0000 | 0.8413 | +0.1587 | 3.489 | 2.248 |
| TELEPHONENUM | 41.087 | 1.0000 | 0.8433 | +0.1567 | 1.701 | 12.931 |
| BUILDINGNUM | 47.496 | 1.0000 | 0.8514 | +0.1486 | 7.278 | 6.756 |
| PROVINCE | 51.082 | 1.0000 | 0.8762 | +0.1238 | 11.243 | 12 |
| CITY | 67.172 | 0.9999 | 0.9310 | +0.0689 | 5.868 | 3.218 |
| IBAN | 36.653 | 0.9998 | 0.9395 | +0.0603 | 192 | 4.506 |
| TARGA | 17.423 | 1.0000 | 0.9512 | +0.0487 | 379 | 1.369 |
| ZIPCODE | 41.026 | 1.0000 | 0.9577 | +0.0423 | 1.015 | 2.522 |
| DATE | 62.831 | 1.0000 | 0.9712 | +0.0288 | 1.358 | 2.283 |
| FULLNAME | 130.401 | 0.9999 | 0.9929 | +0.0070 | 218 | 1.637 |
| STREET | 47.632 | 1.0000 | 0.9971 | +0.0029 | 48 | 226 |
| CF | 57.460 | 1.0000 | 0.9995 | +0.0005 | 16 | 36 |
| **MICRO** | **971.204** | **0.9999** | **0.7778** | **+0.2221** | **190.416** | **255.727** |
| MACRO | | 0.9999 | 0.7423 | +0.2576 | | |

### 2.1 Il profilo di errore di `main`

Due pattern distinti, entrambi più compatibili con una **tassonomia diversa** che con una
minore capacità del modello:

- **Solo recall** — `PROVINCE` P 0.9997 / R 0.7799 e `GENDER` P 0.9614 / R 0.3456: quando li
  predice ha ragione quasi sempre, ma ne salta rispettivamente un quarto e due terzi.
- **Più falsi positivi che entità perse** — `ORG` (33.754 FP contro 2.212 miss), `AMOUNT`,
  `DOCID`, `EMAIL`: `main` assegna quei tag a testo che non è PII, o li assegna con
  un'etichetta che questa tassonomia non riconosce come corretta.

---

## 3. `validation_union` — con riserva

36.297 righe, 981.459 entità, max_len 768.

| | v1.5.0 | main |
|---|---:|---:|
| micro-F1 | 0.9997 | 0.7798 |
| macro-F1 | 0.9997 | 0.7455 |
| token accuracy | 0.9999 | 0.9185 |

⚠️ **1.101 righe (3.03%) tagliate a 768 subword → 47.603 parole non valutate.** La metrica è
ottimistica per entrambi i modelli. È lo stesso confronto di `validation_clean`, che gira a
max_len 1152 senza troncamenti: **usare quello**.

---

## Come leggere questi numeri

`validation_clean` e `validation_union` **non sono un held-out neutro**: `validation_union`
coincide con il set di validation di v1.5.0 (36.297 righe, lo stesso `val_rows` del registry),
e `validation_clean` ne è la versione ripulita. Sono la distribuzione su cui v1.5.0 è stato
costruito.

Un 0.9999 su 971.204 entità, con 15 tag su 22 a 1.0000 esatto, è un modello che si sta
misurando in casa propria. Il numero è calcolato correttamente, ma quello che dimostra è
**"`main` non conosce questa tassonomia"**, non "v1.5.0 è 22 punti migliore".

Il confronto ad armi pari è `validation_real`, dove il Δ micro-F1 è **+0.0001** e i due
modelli sono indistinguibili. Il guadagno reale e difendibile di v1.5.0 sta nella copertura di
mascheramento: **60 token di PII in chiaro invece di 72** (§1.1).

### Limiti

- Validation **solo italiana**: le altre 7 lingue del training non sono misurate.
- I 5 tag legali IT-only (`CF`, `PIVA`, `CATASTO`, `DOCID`, `PROVINCE`) in `validation_real`
  sono entità generate iniettate in frasi reali held-out: buon proxy, non eval cieco.
- Support molto sbilanciati (FULLNAME 4.390 vs TARGA 43 in `validation_real`): sui tag rari
  ogni singolo errore vale ~2 punti di F1.
- In produzione affiancare **sempre** la rete regex + checksum (CF / P.IVA / IBAN / carta) al
  modello: sui formati con checksum la verifica matematica ha priorità sulla predizione.

---

## Riproducibilità

```bash
# metriche strict entity-level
python src/training/evaluate_pii.py \
  --model <path-o-repo-HF> \
  --data dataset/clean/validation_clean.jsonl \
  --max-len 1152 --out experiments/hf_compare/eval_clean_v150

# vista strict / relaxed / masking
python src/training/evaluate_relaxed.py \
  --model <path-o-repo-HF> \
  --data dataset/validation/validation_real.jsonl \
  --max-len 1152 --out experiments/hf_compare/relaxed_real_v150
```

Report grezzi (`.txt` + `.json` per-tag) in `experiments/hf_compare/`.

Metriche entity-level calcolate a mano dentro gli script (niente `seqeval`, non compila su
questo ambiente). "Entità perse" e "falsi positivi" nelle tabelle sono derivati da
support / precision / recall, quindi arrotondati all'unità.

---

*Generato l'8 agosto 2026 · confronto `v1.5.0` vs `main` di `rizzoaiacademy/rizzo-pii-0.3B`*
