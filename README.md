# Bot Vinted -> Telegram per reseller

Questo progetto crea un bot Telegram che guida l'utente nel setup e poi invia notifiche quando su Vinted compaiono nuovi articoli compatibili con i filtri scelti:

- **Marca**
- **Genere** (Uomo/Donna)
- **Tipologia di capo** (es. t-shirt, camicie, giacche e blazer, pantaloni, pantaloncini...)
- **Prezzo massimo**

## Flusso utente

1. L'utente avvia il bot con `/start`.
2. Sceglie la marca tra quelle proposte.
3. Sceglie il genere (Uomo o Donna) tra le opzioni disponibili su Vinted.
4. Sceglie la tipologia di capo proposta dal catalogo Vinted per quel genere.
5. Inserisce il prezzo massimo.
6. Il bot salva la configurazione e controlla periodicamente Vinted.
7. Quando trova nuovi articoli coerenti, invia un messaggio su Telegram con **foto, titolo, prezzo e link diretto**.

Comandi utili:

- `/start` -> avvia o riconfigura
- `/status` -> mostra filtri attivi
- `/stop` -> disattiva monitoraggio

## Setup rapido

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
```

Configura variabili ambiente:

```bash
export TELEGRAM_BOT_TOKEN="<token_botfather>"
export POLLING_INTERVAL_SECONDS=45
# opzionale
export VINTED_BASE_URL="https://www.vinted.it"
export DATA_FILE="data/user_preferences.json"
```

Avvio:

```bash
PYTHONPATH=src python -m vinted_bot.main
```

## Note tecniche

- Il bot carica dinamicamente il catalogo Vinted per mostrare genere e categorie più allineate possibili al filtro reale del sito.
- La ricerca imposta i filtri Vinted con **marca**, **genere**, **categoria capo**, **prezzo massimo** e forza sempre **Ordina per -> Dal più recente**.
- Il bot prova a risolvere automaticamente `brand_id` e `catalog_id` dagli endpoint Vinted per applicare i filtri in modo più fedele.
- Le preferenze utente sono salvate in un file JSON locale.
- Al primo giro di sincronizzazione il bot non notifica gli annunci già esistenti (evita spam), ma solo i nuovi successivi.
- Vinted non offre API pubbliche ufficiali per questo uso: il parser usa endpoint web e potrebbe richiedere manutenzione se cambiano i payload.


## Troubleshooting

- Se in chat vedi ancora il vecchio flusso (solo marca + prezzo), assicurati di aver riavviato il processo del bot dopo l'ultimo pull/aggiornamento del codice.
- Usa sempre `/start` per rifare il setup completo: il comando resetta i dati temporanei della conversazione e riapre i 4 step (marca, genere, categoria, prezzo).
