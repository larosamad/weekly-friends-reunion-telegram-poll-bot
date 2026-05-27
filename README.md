## Weekly Poll Flow

```text
DOMENICA ore 11:00 (ora italiana invernale)
oppure 12:00 (ora italiana estiva)
│
├─ Parte il primo sondaggio
│  ├─ anonimo
│  ├─ scelta multipla
│  └─ scadenza: 22 ore
│
▼
LUNEDÌ ore 09:00-10:00
│
├─ Il primo sondaggio viene chiuso
│
├─ "Non posso" viene ignorato
│
├─ Se c’è un vincitore unico
│  └─ Il bot manda il messaggio:
│
│     "Ciccini del {giorno vincitore}
│      palesatevi con la vostra id reaction
│      e proponete eventuali film nei commenti"
│
└─ Se c’è ex aequo
   └─ Parte il secondo sondaggio
      ├─ anonimo
      ├─ scelta singola
      └─ durata: 8 ore

      ▼
      LUNEDÌ ore 17:00-18:00
      │
      ├─ Il secondo sondaggio viene chiuso
      │
      └─ Il bot manda:
         "Ciccini del {giorno vincitore}
          palesatevi..."
```
