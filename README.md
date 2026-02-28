# Bot Vinted -> Telegram per reseller

Questo progetto crea un bot Telegram che guida l'utente nel setup e poi invia notifiche quando su Vinted compaiono nuovi articoli compatibili con:

- **Marca** (scelta da tastiera)
- **Prezzo massimo** (inserito dall'utente)

## Flusso utente

1. L'utente avvia il bot con `/start`.
2. Sceglie la marca tra quelle proposte.
3. Inserisce il prezzo massimo.
4. Il bot salva la configurazione e controlla periodicamente Vinted.
5. Quando trova nuovi articoli coerenti, invia un messaggio su Telegram.

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
export TELEGRAM_BOT_TOKEN="8358710457:AAEoPguquKqYizzvPt8FM7fQeVFXQWTp3f4"
export POLLING_INTERVAL_SECONDS=5
# opzionale
export VINTED_BASE_URL="https://www.vinted.it"
export DATA_FILE="data/user_preferences.json"
```

Avvio:

```bash
PYTHONPATH=src python -m vinted_bot.main
```

## Note tecniche

- Le preferenze utente sono salvate in un file JSON locale.
- Al primo giro di sincronizzazione il bot **non** notifica gli annunci già esistenti (evita spam), ma solo i nuovi successivi.
- Vinted non offre API pubbliche ufficiali per questo uso: il parser usa endpoint web e potrebbe richiedere manutenzione se cambiano i payload.
