"""
Funzioni per preparare i dati per l'analisi con Claude AI.
Crea prompt formattati per interagire con Claude nelle conversazioni sulla ricerca di lavoro.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

def prepare_claude_prompt(job_file: str) -> Optional[str]:
    """
    Prepara un prompt per Claude basato su un file di un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        
    Returns:
        Testo del prompt per Claude, o None se si verifica un errore
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Estrai i punti chiave dall'offerta
        job_title = job_data.get('Title', 'Offerta senza titolo')
        company_name = job_data.get('Company Name', 'Azienda sconosciuta')
        location = job_data.get('Location', 'Località non specificata')
        job_url = job_data.get('Detail URL', '')
        created_at = job_data.get('Created At', 'Data non specificata')
        description = job_data.get('Description', 'Nessuna descrizione disponibile')
        company_description = job_data.get('Company Description', 'Nessuna descrizione disponibile')
        industry = job_data.get('Industry', 'Non specificato')
        employee_count = job_data.get('Employee Count', 'Non specificato')
        headquarters = job_data.get('Headquarters', 'Non specificato')
        company_founded = job_data.get('Company Founded', 'Non specificato')
        specialties = job_data.get('Specialties', 'Non specificato')
        company_website = job_data.get('Company Website', 'Non specificato')
        
        # Ottieni informazioni sulla rilevanza se disponibili
        relevance_info = ""
        if 'Relevance' in job_data:
            relevance = job_data['Relevance']
            relevance_info = f"""
# Rilevanza per il tuo profilo
- **Punteggio di rilevanza**: {relevance.get('Score', 0)}
- **Angular menzionato**: {"Sì" if relevance.get('Angular Mentioned', False) else "No"}
- **TypeScript menzionato**: {"Sì" if relevance.get('TypeScript Mentioned', False) else "No"}
- **Parole chiave cercate**: {", ".join(relevance.get('Keywords', []))}
"""
        
        # Ottieni informazioni sullo stato della candidatura se disponibili
        application_info = ""
        if 'Application' in job_data:
            application = job_data['Application']
            status = application.get('Status', 'Not Applied')
            applied_date = application.get('Applied Date', 'N/A')
            priority = application.get('Priority', 'Medium')
            interest = application.get('Interest Level', 'Medium')
            
            application_info = f"""
# Stato candidatura
- **Stato attuale**: {status}
- **Data candidatura**: {applied_date if applied_date else "Non ancora applicato"}
- **Priorità**: {priority}
- **Livello di interesse**: {interest}
"""
        
        # Crea il prompt completo per Claude
        prompt = f"""
Questa è un'offerta di lavoro che ho trovato su LinkedIn. Aiutami ad analizzarla e decidere se candidarmi.

# Dettagli dell'offerta
- **Titolo**: {job_title}
- **Azienda**: {company_name}
- **Luogo**: {location}
- **URL**: {job_url}
- **Data pubblicazione**: {created_at}

# Descrizione del lavoro
{description}

# Informazioni sull'azienda
{company_description}
- **Settore**: {industry}
- **Numero dipendenti**: {employee_count}
- **Sede centrale**: {headquarters}
- **Anno fondazione**: {company_founded}
- **Specializzazioni**: {specialties}
- **Sito web**: {company_website}
{relevance_info}
{application_info}

# Richieste per Claude
1. Analizza questa offerta di lavoro e determina se corrisponde al mio profilo di sviluppatore front-end con esperienza in Angular
2. Evidenzia i punti di forza e le potenziali criticità dell'offerta
3. Se ritieni che l'offerta sia adatta, aiutami a preparare una lettera di presentazione personalizzata in italiano
4. Suggeriscimi eventuali modifiche da apportare al CV per massimizzare le possibilità di colloquio

Grazie!
"""
        
        logging.info(f"Prompt per Claude generato con successo per {job_file}")
        return prompt
    except Exception as e:
        logging.error(f"Errore nella preparazione del prompt per Claude: {str(e)}")
        return None


def prepare_cover_letter_prompt(job_file: str) -> Optional[str]:
    """
    Prepara un prompt specifico per la generazione di una lettera di presentazione.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        
    Returns:
        Testo del prompt per Claude, o None se si verifica un errore
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Estrai i punti chiave dall'offerta
        job_title = job_data.get('Title', 'Offerta senza titolo')
        company_name = job_data.get('Company Name', 'Azienda sconosciuta')
        location = job_data.get('Location', 'Località non specificata')
        description = job_data.get('Description', 'Nessuna descrizione disponibile')
        company_description = job_data.get('Company Description', 'Nessuna descrizione disponibile')
        industry = job_data.get('Industry', 'Non specificato')
        
        # Crea il prompt per la lettera di presentazione
        prompt = f"""
Aiutami a creare una lettera di presentazione professionale e persuasiva per questa posizione:

# Dettagli dell'offerta
- **Titolo**: {job_title}
- **Azienda**: {company_name}
- **Luogo**: {location}
- **Settore**: {industry}

# Descrizione del lavoro
{description}

# Descrizione dell'azienda
{company_description}

# Il mio profilo
Sono uno sviluppatore front-end senior con oltre 10 anni di esperienza professionale, specializzato in Angular. Ho una forte esperienza nella creazione di applicazioni web responsive e accessibili. Ho lavorato con Angular (dalla versione 2+), RxJS, NgRX, TypeScript, HTML5 e CSS3. Conosco le migliori pratiche per la creazione di interfacce utente intuitive e per garantire un'esperienza utente ottimale. Sono abituato a lavorare in ambienti agili e sono un buon comunicatore.

# Richieste per Claude
1. Crea una lettera di presentazione professionale in italiano, personalizzata per questa specifica posizione e azienda
2. Enfatizza come le mie competenze Angular, TypeScript e front-end si allineano con i requisiti dell'offerta
3. Metti in evidenza la mia esperienza di 10+ anni e la mia capacità di lavorare in team
4. Mantieni un tono professionale ma personale
5. La lettera deve essere convincente e spiegare in modo chiaro perché sono il candidato ideale
6. Limita la lunghezza a circa 300-400 parole

Grazie!
"""
        
        logging.info(f"Prompt per lettera di presentazione generato con successo per {job_file}")
        return prompt
    except Exception as e:
        logging.error(f"Errore nella preparazione del prompt per la lettera di presentazione: {str(e)}")
        return None


def save_claude_response(job_file: str, response_type: str, content: str) -> bool:
    """
    Salva la risposta di Claude nel file dell'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        response_type: Tipo di risposta (es. "cover_letter", "analysis")
        content: Contenuto della risposta di Claude
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Claude esista
        if 'Claude' not in job_data:
            job_data['Claude'] = {}
        
        # Salva la risposta nella sezione appropriata
        job_data['Claude'][response_type] = content
        
        # Se è una lettera di presentazione, salvala anche nell'oggetto Application
        if response_type == "cover_letter" and 'Application' in job_data:
            job_data['Application']['Cover Letter'] = content
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Risposta di Claude salvata nel file dell'offerta: {job_file}")
        return True
    except Exception as e:
        logging.error(f"Errore nel salvataggio della risposta di Claude: {str(e)}")
        return False


def create_claude_batch_prompt(jobs_index_file: str, max_jobs: int = 5, status_filter: str = "Not Applied") -> Optional[str]:
    """
    Crea un prompt per Claude per analizzare un lotto di offerte.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        max_jobs: Numero massimo di offerte da includere nel prompt
        status_filter: Filtro per lo stato delle offerte
        
    Returns:
        Testo del prompt per Claude, o None se si verifica un errore
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Filtra le offerte per stato
        filtered_jobs = [job for job in index if job.get('Status') == status_filter]
        
        # Limita al numero massimo
        top_jobs = filtered_jobs[:max_jobs]
        
        if not top_jobs:
            logging.warning(f"Nessuna offerta trovata con stato '{status_filter}'")
            return None
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Raccogli i dati per ogni offerta selezionata
        job_summaries = []
        for job_index in top_jobs:
            job_id = job_index.get('JobId')
            title = job_index.get('Title', 'Offerta senza titolo')
            company = job_index.get('Company', 'Azienda sconosciuta')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Crea un riassunto dell'offerta
            summary = f"""
## {title} - {company}
- **Posizione**: {job_data.get('Location', 'Non specificata')}
- **URL**: {job_data.get('Detail URL', '')}
- **Data pubblicazione**: {job_data.get('Created At', 'Non specificata')}
- **Rilevanza**: {job_index.get('Relevance', 0)}

### Estratto descrizione
{job_data.get('Description', 'Nessuna descrizione disponibile')[:300]}...
"""
            job_summaries.append(summary)
        
        # Crea il prompt completo
        prompt = f"""
# Analisi in blocco di offerte di lavoro

Ho trovato queste {len(job_summaries)} offerte di lavoro che potrebbero essere interessanti per me. Potresti dare un'occhiata a queste offerte e aiutarmi a prioritizzarle per la candidatura?

{chr(10).join(job_summaries)}

# Richieste per Claude
1. Analizza brevemente ogni offerta e valuta quanto è adatta al mio profilo di sviluppatore front-end Angular senior
2. Ordina le offerte dalla più alla meno interessante in base alla rilevanza per il mio profilo
3. Per le prime 3 offerte più promettenti, spiega perché dovrei considerarle e quali punti specifici dovrei evidenziare nella candidatura
4. Ci sono offerte che dovrei evitare? Se sì, perché?

Grazie per la tua assistenza!
"""
        
        logging.info(f"Prompt batch per Claude generato con successo per {len(job_summaries)} offerte")
        return prompt
    except Exception as e:
        logging.error(f"Errore nella preparazione del prompt batch per Claude: {str(e)}")
        return None


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Generatore di prompt per Claude')
    parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    parser.add_argument('--type', choices=['general', 'cover_letter', 'batch'], default='general',
                       help='Tipo di prompt da generare')
    parser.add_argument('--max-jobs', type=int, default=5,
                       help='Numero massimo di offerte per prompt batch')
    parser.add_argument('--status-filter', default='Not Applied',
                       help='Filtro per stato offerte (solo per batch)')
    
    args = parser.parse_args()
    
    # Genera il prompt appropriato
    if args.type == 'general':
        prompt = prepare_claude_prompt(args.job_file)
    elif args.type == 'cover_letter':
        prompt = prepare_cover_letter_prompt(args.job_file)
    elif args.type == 'batch':
        prompt = create_claude_batch_prompt(args.job_file, args.max_jobs, args.status_filter)
    else:
        prompt = None
    
    # Stampa il prompt o l'errore
    if prompt:
        print(prompt)
        sys.exit(0)
    else:
        print("Errore nella generazione del prompt", file=sys.stderr)
        sys.exit(1)
