# 🇮🇹 Weekly Poll Bot 

A Telegram bot that automatically runs a weekly poll to decide which day the group wants to meet up. Powered by GitHub Actions — no server required.

## How it works

Il sondaggio parte ogni settimana nel giorno e all’ora salvati dall’app.
Il valore iniziale è **domenica alle 11:07, ora italiana**. Il primo sondaggio
rimane aperto 22 ore; se serve uno spareggio, quest’ultimo dura 8 ore.
Giorno, ora e durate sono personalizzabili nello step 5 dell’app.

Alla chiusura del primo sondaggio il bot annuncia il vincitore oppure apre uno
spareggio tra le opzioni a pari merito, se hanno raggiunto la soglia di voti.

Il workflow controlla la programmazione ogni 15 minuti. GitHub può ritardare
o saltare un’esecuzione: gli orari non sono garantiti al minuto. Il bot recupera
una partenza in ritardo finché non è trascorsa l’intera durata prevista del primo
sondaggio; oltre quella finestra aspetta la settimana successiva.
Le durate decorrono dall’invio effettivo dei rispettivi sondaggi.

## Setup

### 1. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy the **bot token**

### 2. Get the chat ID

1. Add the bot to your group
2. Send a message in the group
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser
4. Find the `"id"` field inside `"chat"` — that is your chat ID (it will be a negative number for groups)

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Description |
|--------|-------------|
| `BOT_TOKEN` | The token you got from BotFather |
| `CHAT_ID` | The Telegram group chat ID (negative number) |

### 4. Enable write permissions for Actions

Go to **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**.

This is needed so the workflow can commit `poll_info.json` to the repo.

### 5. Deploy

Pubblica tutti i file, incluso il workflow aggiornato, nel branch predefinito della tua copia. Abilita Actions per attivare i controlli della programmazione.

You can also run it manually from **Actions → Telegram weekly poll → Run workflow**.

## Manual trigger

The workflow can be triggered manually with a specific mode:

| Mode | Description |
|------|-------------|
| `auto` | Checks the saved weekly schedule and active deadlines |
| `start` | Opens poll 1 immediately if none is active |
| `close_first` | Closes poll 1, announces winner or opens tiebreak |
| `close_tiebreak` | Closes poll 2 and announces winner |

## Files

| File | Description |
|------|-------------|
| `bot.py` | Main bot logic |
| `.github/workflows/telegram-poll.yml` | GitHub Actions workflow |
| `poll_info.json` | Auto-generated — active poll, closing deadline and cached results |
| `schedule_state.json` | Auto-generated — last weekly cycle sent, retained after closing |
| `scheduler.py` | Weekly scheduling and checks without Telegram dependencies |
| `requirements.txt` | Python dependencies |

## Requirements

`requirements.txt`:
```
python-telegram-bot
```

## Configurazione dall’app Friends Reunion

`bot_config.json` contiene le impostazioni modificabili dall’app. `config.py`
le valida e `bot.py` le legge a ogni esecuzione. I valori iniziali mantengono
le opzioni, le domande, il nome del gruppo e la soglia dello spareggio esistenti.

| Campo | Uso |
|---|---|
| `OPTIONS` | Da 2 a 12 risposte, ciascuna da 1 a 100 caratteri |
| `EXCLUDED_OPTION` | Risposta esclusa dalla vittoria; deve coincidere con una delle opzioni |
| `MIN_TIEBREAK_VOTES` | Voti minimi per aprire lo spareggio in caso di parità |
| `FIRST_POLL_QUESTION` | Domanda del primo sondaggio, massimo 300 caratteri |
| `TIEBREAK_QUESTION` | Domanda dello spareggio, massimo 300 caratteri |
| `GROUP_NAME` | Nome usato nel messaggio del vincitore, massimo 100 caratteri |

Un nuovo fork include automaticamente `bot_config.json` e `config.py`.
Per aggiornare una copia esistente usa **Sync fork → Update branch** su GitHub.
Il bot deve ricevere anche il nuovo `bot.py`: aggiungere solo il JSON non basta.

Nell’app usa il proprietario, il repository e il branch della tua copia.
Il token GitHub deve includere quella copia con **Contents: Read and write**
per caricare e salvare le impostazioni, e **Actions: Read and write** per avviare
la prova. Il workflow rimane `telegram-poll.yml`.

Non inserire credenziali nel JSON: `BOT_TOKEN` e `CHAT_ID` restano nei GitHub
Secrets. Le modifiche alle impostazioni vengono lette alla prossima esecuzione;
non riscrivono i messaggi Telegram già inviati. Lo stato del sondaggio continua
a essere salvato dal workflow in `poll_info.json`.

Test locali senza credenziali e senza inviare messaggi:

```sh
python3 -m unittest discover -s tests -v
```

## Programmazione settimanale

La chiave `SCHEDULE` in `bot_config.json` contiene:

```json
{
  "weekday": 6,
  "time": "11:07",
  "timezone": "Europe/Rome",
  "first_poll_hours": 22,
  "tiebreak_hours": 8
}
```

`weekday` va da 0 (lunedì) a 6 (domenica). Le durate sono ore intere positive,
per un totale inferiore a 168 ore. I file precedenti senza `SCHEDULE` usano i
valori iniziali. L’ora legale italiana è gestita automaticamente. Un orario
inesistente durante il cambio primaverile viene spostato dopo il salto; durante
il cambio autunnale viene usata la prima occorrenza dell’ora ripetuta.

Le scadenze di un sondaggio già inviato e la durata del suo eventuale spareggio
restano quelle assegnate alla partenza. Cambiare giorno o ora non invia un secondo
ciclo nella stessa settimana già gestita. Un sondaggio attivo ha sempre priorità:
il successivo non parte finché quello precedente non è concluso.

Lo stato viene salvato sul branch eseguito e associato a repository e gruppo.
Un nuovo fork ignora lo stato con un’associazione diversa. Non eliminare
`schedule_state.json`: serve a ricordare che l’invio settimanale è già avvenuto.
Un vecchio `poll_info.json` senza scadenza viene mantenuto e riceve una scadenza
pari alla durata configurata a partire dal primo controllo dopo l’aggiornamento.

Per attivare la funzione su un fork esistente, sincronizza anche `scheduler.py`,
`config.py`, `bot.py` e `.github/workflows/telegram-poll.yml`, non solo il JSON.
Le esecuzioni programmate leggono il branch predefinito. L’app può rimanere chiusa.
I controlli periodici utilizzano la quota GitHub Actions del proprietario della copia.
Se il salvataggio dello stato fallisce dopo un invio Telegram, controlla l’esecuzione
prima di rilanciarla: l’invio e il commit su GitHub non sono una transazione unica.
