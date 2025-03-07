# LinkedIn Job Scraper

Uno strumento Python per automatizzare la ricerca e l'analisi di offerte di lavoro su LinkedIn, con integrazione per Claude AI.

## 🚀 Caratteristiche

- Scraping etico di annunci di lavoro da LinkedIn
- Supporto per ricerche singole e multiple con vari filtri
- Esportazione dei dati in formato JSON
- Generazione di file individuali per ogni annuncio
- Preparazione di prompt per analisi con Claude AI
- Integrazione con sistemi di tracciamento delle candidature
- Misure anti-bot per evitare blocchi

## 📋 Requisiti

- Python 3.8+
- Connessione internet
- Account LinkedIn (opzionale, ma consigliato)

## 🔧 Installazione

1. Clona il repository:
```bash
git clone https://github.com/yourusername/linkedin-job-scraper.git
cd linkedin-job-scraper
```

2. Crea un ambiente virtuale e attivalo:
```bash
python -m venv venv
# Su Windows
venv\Scripts\activate
# Su macOS/Linux
source venv/bin/activate
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

4. Copia il file di configurazione:
```bash
cp .env.example .env
```

## 💻 Utilizzo

### Ricerca semplice
```bash
python -m linkedin_job_scraper --keywords="front end developer" --location="Italy" --remote
```

### Ricerca avanzata con esportazione individuale
```bash
python -m linkedin_job_scraper --keywords="angular developer OR react developer" --location="Italy" --remote --seniority mid-senior --recent --export-individual
```

### Utilizzo di un URL di ricerca esistente
```bash
python -m linkedin_job_scraper "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=..."
```

### Scraping di un singolo annuncio
```bash
python -m linkedin_job_scraper "https://www.linkedin.com/jobs/view/3887695775/"
```

## 🔄 Flusso di lavoro con Claude

1. Esegui lo scraper con esportazione individuale
2. Controlla il file di indice `jobs_index.json` per identificare gli annunci più rilevanti
3. Per ogni annuncio interessante, utilizza il comando per generare un prompt per Claude:
```bash
python -m linkedin_job_scraper.exporters.claude_exporter job_files/12345_CompanyName_JobTitle.json
```
4. Crea una nuova chat con Claude e incolla il prompt generato
5. Interagisci con Claude per analizzare l'annuncio e preparare la candidatura
6. Aggiorna il tracker delle candidature con i risultati

## 📊 Schema dei dati

Lo schema JSON utilizzato è compatibile con molti sistemi di tracciamento delle candidature e include:
- Informazioni di base sull'annuncio (titolo, descrizione, URL)
- Dettagli dell'azienda
- Stato della candidatura
- Punteggio di rilevanza basato su parole chiave

## 🛡️ Considerazioni etiche e legali

Questo tool è progettato per automatizzare la ricerca di lavoro personale, non per raccolta massiva di dati. Si prega di:
- Rispettare i limiti di richieste per evitare sovraccarichi
- Utilizzare ritardi tra le richieste (inclusi di default)
- Non condividere i dati raccolti senza autorizzazione
- Rispettare i Termini di Servizio di LinkedIn

## 📝 Licenza

MIT License

## 🤝 Contribuire

Contributi, segnalazioni di bug e richieste di funzionalità sono benvenuti!
