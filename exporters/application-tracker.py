"""
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts[status] = count
        
        # Calcola le date più recenti di attività
        latest_scraped = max([job.get('ScrapedDate', '2000-01-01') for job in index], default='N/A')
        
        applied_jobs = [job for job in index if job.get('Status') != 'Not Applied' and job.get('AppliedDate')]
        latest_applied = max([job.get('AppliedDate', '2000-01-01') for job in applied_jobs], default='N/A')
        
        # Genera il report nel formato richiesto
        if format_type == 'markdown':
            report = _generate_markdown_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'html':
            report = _generate_html_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'csv':
            report = _generate_csv_report(index, output_file)
        else:
            logging.error(f"Formato non supportato: {format_type}")
            return None
        
        # Salva il report se è specificato un file di output
        if output_file and format_type != 'csv':  # Il CSV è già salvato nella funzione
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report salvato in {output_file}")
        
        return report
    except Exception as e:
        logging.error(f"Errore nella generazione del report: {str(e)}")
        return None


def _generate_markdown_report(index: List[Dict[str, Any]], total_jobs: int,
                            status_counts: Dict[str, int], latest_scraped: str,
                            latest_applied: str) -> str:
    """
    Genera un report in formato Markdown.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato Markdown
    """
    # Intestazione del report
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Report delle Candidature di Lavoro

Generato il: {now}

## Statistiche Generali

- **Offerte totali monitorate**: {total_jobs}
- **Ultima offerta scrappata**: {latest_scraped}
- **Ultima candidatura inviata**: {latest_applied}

## Stato delle Candidature

| Stato | Conteggio | Percentuale |
|-------|-----------|-------------|
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            report += f"| {status} | {count} | {percentage:.1f}% |\n"
        else:
            report += f"| {status} | {count} | 0% |\n"
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        report += "\n## Candidature Attive\n\n"
        report += "| Azienda | Titolo | Stato | Data Candidatura |\n"
        report += "|---------|--------|-------|------------------|\n"
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            report += f"| {company} | {title} | {status} | {applied_date} |\n"
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        report += "\n## Nuove Offerte Interessanti\n\n"
        report += "| Azienda | Titolo | Rilevanza | Posizione |\n"
        report += "|---------|--------|-----------|----------|\n"
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            report += f"| {company} | {title} | {relevance} | {location} |\n"
    
    return report


def _generate_html_report(index: List[Dict[str, Any]], total_jobs: int,
                         status_counts: Dict[str, int], latest_scraped: str,
                         latest_applied: str) -> str:
    """
    Genera un report in formato HTML.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato HTML
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Candidature Lavoro</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #2a5885; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2a5885; }}
        .progress-container {{ background-color: #e0e0e0; border-radius: 5px; margin-top: 5px; }}
        .progress-bar {{ background-color: #4CAF50; height: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report delle Candidature di Lavoro</h1>
    <p>Generato il: {now}</p>
    
    <h2>Statistiche Generali</h2>
    <div class="stats">
        <div class="stat-card">
            <div>Offerte Totali</div>
            <div class="stat-value">{total_jobs}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Offerta Scrappata</div>
            <div class="stat-value">{latest_scraped.split('T')[0] if 'T' in latest_scraped else latest_scraped}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Candidatura</div>
            <div class="stat-value">{latest_applied.split('T')[0] if 'T' in latest_applied else latest_applied}</div>
        </div>
    </div>
    
    <h2>Stato delle Candidature</h2>
    <table>
        <tr>
            <th>Stato</th>
            <th>Conteggio</th>
            <th>Percentuale</th>
            <th>Progresso</th>
        </tr>
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {percentage}%;"></div>
                </div>
            </td>
        </tr>"""
        else:
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>0%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%;"></div>
                </div>
            </td>
        </tr>"""
    
    html += """
    </table>
    """
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        html += """
    <h2>Candidature Attive</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Stato</th>
            <th>Data Candidatura</th>
        </tr>
"""
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{status}</td>
            <td>{applied_date}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        html += """
    <h2>Nuove Offerte Interessanti</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Rilevanza</th>
            <th>Posizione</th>
        </tr>
"""
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{relevance}</td>
            <td>{location}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    html += """
</body>
</html>
"""
    
    return html


def _generate_csv_report(index: List[Dict[str, Any]], output_file: str) -> str:
    """
    Genera un report in formato CSV.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        output_file: Percorso al file di output
        
    Returns:
        Messaggio di successo
    """
    if not output_file:
        output_file = f"job_applications_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    
    # Definisci i campi CSV
    fieldnames = [
        'JobId', 'Title', 'Company', 'Location', 'RemoteStatus',
        'DetailURL', 'PostedDate', 'ScrapedDate', 'Status',
        'AppliedDate', 'Priority', 'InterestLevel', 'Relevance'
    ]
    
    # Scrivi il file CSV
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in index:
                # Filtra solo i campi che vogliamo nel CSV
                job_row = {field: job.get(field, '') for field in fieldnames if field in job}
                writer.writerow(job_row)
        
        logging.info(f"File CSV salvato in {output_file}")
        return f"Report CSV generato con successo e salvato in {output_file}"
    except Exception as e:
        logging.error(f"Errore nella creazione del file CSV: {str(e)}")
        return f"Errore nella generazione del report CSV: {str(e)}"


def update_application_status(job_file: str, new_status: str, notes: str = None, 
                            applied_date: str = None) -> bool:
    """
    Aggiorna lo stato della candidatura per un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        new_status: Nuovo stato della candidatura
        notes: Note opzionali da aggiungere
        applied_date: Data di candidatura (se diversa da oggi)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Imposta la data di oggi come predefinita se non specificata
        if not applied_date:
            if new_status == 'Applied' and job_data['Application']['Status'] == 'Not Applied':
                applied_date = datetime.datetime.now().isoformat()
        
        # Aggiorna lo stato della candidatura
        old_status = job_data['Application']['Status']
        job_data['Application']['Status'] = new_status
        
        # Aggiorna i campi relativi alla data in base allo stato
        if new_status == 'Applied' and applied_date:
            job_data['Application']['Applied Date'] = applied_date
        elif new_status == 'Screening':
            job_data['Application']['Response Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Interview':
            job_data['Application']['Interview Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Offer':
            job_data['Application']['Offer Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Rejected':
            job_data['Application']['Rejection Date'] = datetime.datetime.now().isoformat()
        
        # Aggiorna le note se fornite
        if notes:
            if job_data['Application']['Notes']:
                job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato da '{old_status}' a '{new_status}' per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_for_job(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura: {str(e)}")
        return False


def update_index_for_job(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna l'indice per un'offerta specifica.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta dall'URL
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            logging.error("Impossibile estrarre l'ID dell'offerta dai dati")
            return False
        
        # Trova la voce corrispondente nell'indice
        updated = False
        for job_entry in index:
            if job_entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice con i dati dell'offerta
                if 'Application' in job_data:
                    job_entry['Status'] = job_data['Application'].get('Status', 'Not Applied')
                    job_entry['AppliedDate'] = job_data['Application'].get('Applied Date')
                    job_entry['Priority'] = job_data['Application'].get('Priority', 'Medium')
                    job_entry['InterestLevel'] = job_data['Application'].get('Interest Level', 'Medium')
                updated = True
                break
        
        if not updated:
            logging.warning(f"Nessuna voce trovata nell'indice per l'offerta con ID {job_id}")
            return False
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta con ID {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False


def export_to_external_tracker(jobs_index_file: str, format_type: str = 'csv',
                             output_file: str = None) -> bool:
    """
    Esporta i dati delle candidature in un formato compatibile con tracker esterni.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        format_type: Formato di esportazione ('csv', 'json', 'excel')
        output_file: Percorso al file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        if format_type == 'csv':
            result = _generate_csv_report(index, output_file)
            return "Errore" not in result
        else:
            logging.error(f"Formato di esportazione non supportato: {format_type}")
            return False
    except Exception as e:
        logging.error(f"Errore nell'esportazione dei dati: {str(e)}")
        return False


def set_reminder_for_followup(job_file: str, reminder_date: str = None, 
                            days_from_now: int = 7) -> bool:
    """
    Imposta un promemoria per il follow-up di una candidatura.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        reminder_date: Data del promemoria (formato ISO)
        days_from_now: Giorni da oggi per il promemoria (se reminder_date non è specificato)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Calcola la data del promemoria se non specificata
        if not reminder_date:
            reminder_date = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).isoformat()
        
        # Imposta la data del promemoria
        job_data['Application']['Follow Up Date'] = reminder_date
        
        # Aggiorna le note
        reminder_note = f"Promemoria per follow-up impostato per {reminder_date.split('T')[0] if 'T' in reminder_date else reminder_date}"
        
        if job_data['Application']['Notes']:
            job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        else:
            job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Promemoria per follow-up impostato per {reminder_date} ({job_file})")
        return True
    except Exception as e:
        logging.error(f"Errore nell'impostazione del promemoria per follow-up: {str(e)}")
        return False


def get_due_followups(jobs_index_file: str) -> List[Dict[str, Any]]:
    """
    Ottiene una lista di offerte che necessitano di follow-up.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        
    Returns:
        Lista di offerte che necessitano di follow-up
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        due_followups = []
        today = datetime.datetime.now().date()
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Cerca le offerte che necessitano di follow-up
        for job_index in index:
            job_id = job_index.get('JobId')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Controlla se è necessario un follow-up
            if 'Application' in job_data and job_data['Application'].get('Follow Up Date'):
                followup_date_str = job_data['Application']['Follow Up Date']
                
                # Converte la data in oggetto datetime
                try:
                    if 'T' in followup_date_str:
                        followup_date = datetime.datetime.fromisoformat(followup_date_str).date()
                    else:
                        followup_date = datetime.datetime.strptime(followup_date_str, '%Y-%m-%d').date()
                    
                    # Controlla se la data è oggi o nel passato
                    if followup_date <= today:
                        due_followups.append({
                            'JobId': job_id,
                            'Title': job_data.get('Title'),
                            'Company': job_data.get('Company Name'),
                            'Status': job_data['Application'].get('Status'),
                            'FollowUpDate': followup_date_str,
                            'FilePath': str(job_files[0])
                        })
                except (ValueError, TypeError):
                    continue
        
        # Ordina per data di follow-up
        due_followups.sort(key=lambda x: x.get('FollowUpDate', ''))
        
        return due_followups
    except Exception as e:
        logging.error(f"Errore nell'ottenimento dei follow-up in scadenza: {str(e)}")
        return []


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Gestore del tracciamento delle candidature')
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando per generare un report
    report_parser = subparsers.add_parser('report', help='Genera un report sullo stato delle candidature')
    report_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    report_parser.add_argument('--output', '-o', help='Percorso al file di output')
    report_parser.add_argument('--format', '-f', choices=['markdown', 'html', 'csv'], default='markdown',
                             help='Formato del report')
    
    # Comando per aggiornare lo stato
    status_parser = subparsers.add_parser('update', help='Aggiorna lo stato di una candidatura')
    status_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    status_parser.add_argument('--status', '-s', required=True,
                             choices=['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
                             help='Nuovo stato della candidatura')
    status_parser.add_argument('--notes', '-n', help='Note da aggiungere')
    status_parser.add_argument('--applied-date', '-d', help='Data di candidatura (formato ISO)')
    
    # Comando per impostare un promemoria
    reminder_parser = subparsers.add_parser('reminder', help='Imposta un promemoria per il follow-up')
    reminder_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    reminder_parser.add_argument('--date', '-d', help='Data del promemoria (formato ISO)')
    reminder_parser.add_argument('--days', type=int, default=7, help='Giorni da oggi per il promemoria')
    
    # Comando per ottenere i follow-up in scadenza
    followup_parser = subparsers.add_parser('followups', help='Ottieni le offerte che necessitano di follow-up')
    followup_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    
    # Comando per esportare le candidature
    export_parser = subparsers.add_parser('export', help='Esporta i dati delle candidature')
    export_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    export_parser.add_argument('--output', '-o', help='Percorso al file di output')
    export_parser.add_argument('--format', '-f', choices=['csv', 'json', 'excel'], default='csv',
                             help='Formato di esportazione')
    
    args = parser.parse_args()
    """
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts[status] = count
        
        # Calcola le date più recenti di attività
        latest_scraped = max([job.get('ScrapedDate', '2000-01-01') for job in index], default='N/A')
        
        applied_jobs = [job for job in index if job.get('Status') != 'Not Applied' and job.get('AppliedDate')]
        latest_applied = max([job.get('AppliedDate', '2000-01-01') for job in applied_jobs], default='N/A')
        
        # Genera il report nel formato richiesto
        if format_type == 'markdown':
            report = _generate_markdown_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'html':
            report = _generate_html_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'csv':
            report = _generate_csv_report(index, output_file)
        else:
            logging.error(f"Formato non supportato: {format_type}")
            return None
        
        # Salva il report se è specificato un file di output
        if output_file and format_type != 'csv':  # Il CSV è già salvato nella funzione
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report salvato in {output_file}")
        
        return report
    except Exception as e:
        logging.error(f"Errore nella generazione del report: {str(e)}")
        return None


def _generate_markdown_report(index: List[Dict[str, Any]], total_jobs: int,
                            status_counts: Dict[str, int], latest_scraped: str,
                            latest_applied: str) -> str:
    """
    Genera un report in formato Markdown.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato Markdown
    """
    # Intestazione del report
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Report delle Candidature di Lavoro

Generato il: {now}

## Statistiche Generali

- **Offerte totali monitorate**: {total_jobs}
- **Ultima offerta scrappata**: {latest_scraped}
- **Ultima candidatura inviata**: {latest_applied}

## Stato delle Candidature

| Stato | Conteggio | Percentuale |
|-------|-----------|-------------|
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            report += f"| {status} | {count} | {percentage:.1f}% |\n"
        else:
            report += f"| {status} | {count} | 0% |\n"
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        report += "\n## Candidature Attive\n\n"
        report += "| Azienda | Titolo | Stato | Data Candidatura |\n"
        report += "|---------|--------|-------|------------------|\n"
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            report += f"| {company} | {title} | {status} | {applied_date} |\n"
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        report += "\n## Nuove Offerte Interessanti\n\n"
        report += "| Azienda | Titolo | Rilevanza | Posizione |\n"
        report += "|---------|--------|-----------|----------|\n"
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            report += f"| {company} | {title} | {relevance} | {location} |\n"
    
    return report


def _generate_html_report(index: List[Dict[str, Any]], total_jobs: int,
                         status_counts: Dict[str, int], latest_scraped: str,
                         latest_applied: str) -> str:
    """
    Genera un report in formato HTML.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato HTML
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Candidature Lavoro</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #2a5885; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2a5885; }}
        .progress-container {{ background-color: #e0e0e0; border-radius: 5px; margin-top: 5px; }}
        .progress-bar {{ background-color: #4CAF50; height: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report delle Candidature di Lavoro</h1>
    <p>Generato il: {now}</p>
    
    <h2>Statistiche Generali</h2>
    <div class="stats">
        <div class="stat-card">
            <div>Offerte Totali</div>
            <div class="stat-value">{total_jobs}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Offerta Scrappata</div>
            <div class="stat-value">{latest_scraped.split('T')[0] if 'T' in latest_scraped else latest_scraped}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Candidatura</div>
            <div class="stat-value">{latest_applied.split('T')[0] if 'T' in latest_applied else latest_applied}</div>
        </div>
    </div>
    
    <h2>Stato delle Candidature</h2>
    <table>
        <tr>
            <th>Stato</th>
            <th>Conteggio</th>
            <th>Percentuale</th>
            <th>Progresso</th>
        </tr>
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {percentage}%;"></div>
                </div>
            </td>
        </tr>"""
        else:
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>0%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%;"></div>
                </div>
            </td>
        </tr>"""
    
    html += """
    </table>
    """
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        html += """
    <h2>Candidature Attive</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Stato</th>
            <th>Data Candidatura</th>
        </tr>
"""
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{status}</td>
            <td>{applied_date}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        html += """
    <h2>Nuove Offerte Interessanti</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Rilevanza</th>
            <th>Posizione</th>
        </tr>
"""
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{relevance}</td>
            <td>{location}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    html += """
</body>
</html>
"""
    
    return html


def _generate_csv_report(index: List[Dict[str, Any]], output_file: str) -> str:
    """
    Genera un report in formato CSV.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        output_file: Percorso al file di output
        
    Returns:
        Messaggio di successo
    """
    if not output_file:
        output_file = f"job_applications_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    
    # Definisci i campi CSV
    fieldnames = [
        'JobId', 'Title', 'Company', 'Location', 'RemoteStatus',
        'DetailURL', 'PostedDate', 'ScrapedDate', 'Status',
        'AppliedDate', 'Priority', 'InterestLevel', 'Relevance'
    ]
    
    # Scrivi il file CSV
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in index:
                # Filtra solo i campi che vogliamo nel CSV
                job_row = {field: job.get(field, '') for field in fieldnames if field in job}
                writer.writerow(job_row)
        
        logging.info(f"File CSV salvato in {output_file}")
        return f"Report CSV generato con successo e salvato in {output_file}"
    except Exception as e:
        logging.error(f"Errore nella creazione del file CSV: {str(e)}")
        return f"Errore nella generazione del report CSV: {str(e)}"


def update_application_status(job_file: str, new_status: str, notes: str = None, 
                            applied_date: str = None) -> bool:
    """
    Aggiorna lo stato della candidatura per un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        new_status: Nuovo stato della candidatura
        notes: Note opzionali da aggiungere
        applied_date: Data di candidatura (se diversa da oggi)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Imposta la data di oggi come predefinita se non specificata
        if not applied_date:
            if new_status == 'Applied' and job_data['Application']['Status'] == 'Not Applied':
                applied_date = datetime.datetime.now().isoformat()
        
        # Aggiorna lo stato della candidatura
        old_status = job_data['Application']['Status']
        job_data['Application']['Status'] = new_status
        
        # Aggiorna i campi relativi alla data in base allo stato
        if new_status == 'Applied' and applied_date:
            job_data['Application']['Applied Date'] = applied_date
        elif new_status == 'Screening':
            job_data['Application']['Response Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Interview':
            job_data['Application']['Interview Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Offer':
            job_data['Application']['Offer Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Rejected':
            job_data['Application']['Rejection Date'] = datetime.datetime.now().isoformat()
        
        # Aggiorna le note se fornite
        if notes:
            if job_data['Application']['Notes']:
                job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato da '{old_status}' a '{new_status}' per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_for_job(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura: {str(e)}")
        return False


def update_index_for_job(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna l'indice per un'offerta specifica.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta dall'URL
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            logging.error("Impossibile estrarre l'ID dell'offerta dai dati")
            return False
        
        # Trova la voce corrispondente nell'indice
        updated = False
        for job_entry in index:
            if job_entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice con i dati dell'offerta
                if 'Application' in job_data:
                    job_entry['Status'] = job_data['Application'].get('Status', 'Not Applied')
                    job_entry['AppliedDate'] = job_data['Application'].get('Applied Date')
                    job_entry['Priority'] = job_data['Application'].get('Priority', 'Medium')
                    job_entry['InterestLevel'] = job_data['Application'].get('Interest Level', 'Medium')
                updated = True
                break
        
        if not updated:
            logging.warning(f"Nessuna voce trovata nell'indice per l'offerta con ID {job_id}")
            return False
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta con ID {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False


def export_to_external_tracker(jobs_index_file: str, format_type: str = 'csv',
                             output_file: str = None) -> bool:
    """
    Esporta i dati delle candidature in un formato compatibile con tracker esterni.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        format_type: Formato di esportazione ('csv', 'json', 'excel')
        output_file: Percorso al file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        if format_type == 'csv':
            result = _generate_csv_report(index, output_file)
            return "Errore" not in result
        else:
            logging.error(f"Formato di esportazione non supportato: {format_type}")
            return False
    except Exception as e:
        logging.error(f"Errore nell'esportazione dei dati: {str(e)}")
        return False


def set_reminder_for_followup(job_file: str, reminder_date: str = None, 
                            days_from_now: int = 7) -> bool:
    """
    Imposta un promemoria per il follow-up di una candidatura.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        reminder_date: Data del promemoria (formato ISO)
        days_from_now: Giorni da oggi per il promemoria (se reminder_date non è specificato)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Calcola la data del promemoria se non specificata
        if not reminder_date:
            reminder_date = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).isoformat()
        
        # Imposta la data del promemoria
        job_data['Application']['Follow Up Date'] = reminder_date
        
        # Aggiorna le note
        reminder_note = f"Promemoria per follow-up impostato per {reminder_date.split('T')[0] if 'T' in reminder_date else reminder_date}"
        
        if job_data['Application']['Notes']:
            job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        else:
            job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Promemoria per follow-up impostato per {reminder_date} ({job_file})")
        return True
    except Exception as e:
        logging.error(f"Errore nell'impostazione del promemoria per follow-up: {str(e)}")
        return False


def get_due_followups(jobs_index_file: str) -> List[Dict[str, Any]]:
    """
    Ottiene una lista di offerte che necessitano di follow-up.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        
    Returns:
        Lista di offerte che necessitano di follow-up
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        due_followups = []
        today = datetime.datetime.now().date()
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Cerca le offerte che necessitano di follow-up
        for job_index in index:
            job_id = job_index.get('JobId')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Controlla se è necessario un follow-up
            if 'Application' in job_data and job_data['Application'].get('Follow Up Date'):
                followup_date_str = job_data['Application']['Follow Up Date']
                
                # Converte la data in oggetto datetime
                try:
                    if 'T' in followup_date_str:
                        followup_date = datetime.datetime.fromisoformat(followup_date_str).date()
                    else:
                        followup_date = datetime.datetime.strptime(followup_date_str, '%Y-%m-%d').date()
                    
                    # Controlla se la data è oggi o nel passato
                    if followup_date <= today:
                        due_followups.append({
                            'JobId': job_id,
                            'Title': job_data.get('Title'),
                            'Company': job_data.get('Company Name'),
                            'Status': job_data['Application'].get('Status'),
                            'FollowUpDate': followup_date_str,
                            'FilePath': str(job_files[0])
                        })
                except (ValueError, TypeError):
                    continue
        
        # Ordina per data di follow-up
        due_followups.sort(key=lambda x: x.get('FollowUpDate', ''))
        
        return due_followups
    except Exception as e:
        logging.error(f"Errore nell'ottenimento dei follow-up in scadenza: {str(e)}")
        return []


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Gestore del tracciamento delle candidature')
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando per generare un report
    report_parser = subparsers.add_parser('report', help='Genera un report sullo stato delle candidature')
    report_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    report_parser.add_argument('--output', '-o', help='Percorso al file di output')
    report_parser.add_argument('--format', '-f', choices=['markdown', 'html', 'csv'], default='markdown',
                             help='Formato del report')
    
    # Comando per aggiornare lo stato
    status_parser = subparsers.add_parser('update', help='Aggiorna lo stato di una candidatura')
    status_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    status_parser.add_argument('--status', '-s', required=True,
                             choices=['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
                             help='Nuovo stato della candidatura')
    status_parser.add_argument('--notes', '-n', help='Note da aggiungere')
    status_parser.add_argument('--applied-date', '-d', help='Data di candidatura (formato ISO)')
    
    # Comando per impostare un promemoria
    reminder_parser = subparsers.add_parser('reminder', help='Imposta un promemoria per il follow-up')
    reminder_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    reminder_parser.add_argument('--date', '-d', help='Data del promemoria (formato ISO)')
    reminder_parser.add_argument('--days', type=int, default=7, help='Giorni da oggi per il promemoria')
    
    # Comando per ottenere i follow-up in scadenza
    followup_parser = subparsers.add_parser('followups', help='Ottieni le offerte che necessitano di follow-up')
    followup_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    
    # Comando per esportare le candidature
    export_parser = subparsers.add_parser('export', help='Esporta i dati delle candidature')
    export_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    export_parser.add_argument('--output', '-o', help='Percorso al file di output')
    export_parser.add_argument('--format', '-f', choices=['csv', 'json', 'excel'], default"""
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts[status] = count
        
        # Calcola le date più recenti di attività
        latest_scraped = max([job.get('ScrapedDate', '2000-01-01') for job in index], default='N/A')
        
        applied_jobs = [job for job in index if job.get('Status') != 'Not Applied' and job.get('AppliedDate')]
        latest_applied = max([job.get('AppliedDate', '2000-01-01') for job in applied_jobs], default='N/A')
        
        # Genera il report nel formato richiesto
        if format_type == 'markdown':
            report = _generate_markdown_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'html':
            report = _generate_html_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'csv':
            report = _generate_csv_report(index, output_file)
        else:
            logging.error(f"Formato non supportato: {format_type}")
            return None
        
        # Salva il report se è specificato un file di output
        if output_file and format_type != 'csv':  # Il CSV è già salvato nella funzione
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report salvato in {output_file}")
        
        return report
    except Exception as e:
        logging.error(f"Errore nella generazione del report: {str(e)}")
        return None


def _generate_markdown_report(index: List[Dict[str, Any]], total_jobs: int,
                            status_counts: Dict[str, int], latest_scraped: str,
                            latest_applied: str) -> str:
    """
    Genera un report in formato Markdown.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato Markdown
    """
    # Intestazione del report
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Report delle Candidature di Lavoro

Generato il: {now}

## Statistiche Generali

- **Offerte totali monitorate**: {total_jobs}
- **Ultima offerta scrappata**: {latest_scraped}
- **Ultima candidatura inviata**: {latest_applied}

## Stato delle Candidature

| Stato | Conteggio | Percentuale |
|-------|-----------|-------------|
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            report += f"| {status} | {count} | {percentage:.1f}% |\n"
        else:
            report += f"| {status} | {count} | 0% |\n"
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        report += "\n## Candidature Attive\n\n"
        report += "| Azienda | Titolo | Stato | Data Candidatura |\n"
        report += "|---------|--------|-------|------------------|\n"
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            report += f"| {company} | {title} | {status} | {applied_date} |\n"
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        report += "\n## Nuove Offerte Interessanti\n\n"
        report += "| Azienda | Titolo | Rilevanza | Posizione |\n"
        report += "|---------|--------|-----------|----------|\n"
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            report += f"| {company} | {title} | {relevance} | {location} |\n"
    
    return report


def _generate_html_report(index: List[Dict[str, Any]], total_jobs: int,
                         status_counts: Dict[str, int], latest_scraped: str,
                         latest_applied: str) -> str:
    """
    Genera un report in formato HTML.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato HTML
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Candidature Lavoro</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #2a5885; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2a5885; }}
        .progress-container {{ background-color: #e0e0e0; border-radius: 5px; margin-top: 5px; }}
        .progress-bar {{ background-color: #4CAF50; height: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report delle Candidature di Lavoro</h1>
    <p>Generato il: {now}</p>
    
    <h2>Statistiche Generali</h2>
    <div class="stats">
        <div class="stat-card">
            <div>Offerte Totali</div>
            <div class="stat-value">{total_jobs}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Offerta Scrappata</div>
            <div class="stat-value">{latest_scraped.split('T')[0] if 'T' in latest_scraped else latest_scraped}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Candidatura</div>
            <div class="stat-value">{latest_applied.split('T')[0] if 'T' in latest_applied else latest_applied}</div>
        </div>
    </div>
    
    <h2>Stato delle Candidature</h2>
    <table>
        <tr>
            <th>Stato</th>
            <th>Conteggio</th>
            <th>Percentuale</th>
            <th>Progresso</th>
        </tr>
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {percentage}%;"></div>
                </div>
            </td>
        </tr>"""
        else:
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>0%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%;"></div>
                </div>
            </td>
        </tr>"""
    
    html += """
    </table>
    """
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        html += """
    <h2>Candidature Attive</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Stato</th>
            <th>Data Candidatura</th>
        </tr>
"""
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{status}</td>
            <td>{applied_date}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        html += """
    <h2>Nuove Offerte Interessanti</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Rilevanza</th>
            <th>Posizione</th>
        </tr>
"""
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{relevance}</td>
            <td>{location}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    html += """
</body>
</html>
"""
    
    return html


def _generate_csv_report(index: List[Dict[str, Any]], output_file: str) -> str:
    """
    Genera un report in formato CSV.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        output_file: Percorso al file di output
        
    Returns:
        Messaggio di successo
    """
    if not output_file:
        output_file = f"job_applications_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    
    # Definisci i campi CSV
    fieldnames = [
        'JobId', 'Title', 'Company', 'Location', 'RemoteStatus',
        'DetailURL', 'PostedDate', 'ScrapedDate', 'Status',
        'AppliedDate', 'Priority', 'InterestLevel', 'Relevance'
    ]
    
    # Scrivi il file CSV
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in index:
                # Filtra solo i campi che vogliamo nel CSV
                job_row = {field: job.get(field, '') for field in fieldnames if field in job}
                writer.writerow(job_row)
        
        logging.info(f"File CSV salvato in {output_file}")
        return f"Report CSV generato con successo e salvato in {output_file}"
    except Exception as e:
        logging.error(f"Errore nella creazione del file CSV: {str(e)}")
        return f"Errore nella generazione del report CSV: {str(e)}"


def update_application_status(job_file: str, new_status: str, notes: str = None, 
                            applied_date: str = None) -> bool:
    """
    Aggiorna lo stato della candidatura per un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        new_status: Nuovo stato della candidatura
        notes: Note opzionali da aggiungere
        applied_date: Data di candidatura (se diversa da oggi)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Imposta la data di oggi come predefinita se non specificata
        if not applied_date:
            if new_status == 'Applied' and job_data['Application']['Status'] == 'Not Applied':
                applied_date = datetime.datetime.now().isoformat()
        
        # Aggiorna lo stato della candidatura
        old_status = job_data['Application']['Status']
        job_data['Application']['Status'] = new_status
        
        # Aggiorna i campi relativi alla data in base allo stato
        if new_status == 'Applied' and applied_date:
            job_data['Application']['Applied Date'] = applied_date
        elif new_status == 'Screening':
            job_data['Application']['Response Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Interview':
            job_data['Application']['Interview Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Offer':
            job_data['Application']['Offer Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Rejected':
            job_data['Application']['Rejection Date'] = datetime.datetime.now().isoformat()
        
        # Aggiorna le note se fornite
        if notes:
            if job_data['Application']['Notes']:
                job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato da '{old_status}' a '{new_status}' per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_for_job(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura: {str(e)}")
        return False


def update_index_for_job(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna l'indice per un'offerta specifica.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta dall'URL
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            logging.error("Impossibile estrarre l'ID dell'offerta dai dati")
            return False
        
        # Trova la voce corrispondente nell'indice
        updated = False
        for job_entry in index:
            if job_entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice con i dati dell'offerta
                if 'Application' in job_data:
                    job_entry['Status'] = job_data['Application'].get('Status', 'Not Applied')
                    job_entry['AppliedDate'] = job_data['Application'].get('Applied Date')
                    job_entry['Priority'] = job_data['Application'].get('Priority', 'Medium')
                    job_entry['InterestLevel'] = job_data['Application'].get('Interest Level', 'Medium')
                updated = True
                break
        
        if not updated:
            logging.warning(f"Nessuna voce trovata nell'indice per l'offerta con ID {job_id}")
            return False
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta con ID {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False


def export_to_external_tracker(jobs_index_file: str, format_type: str = 'csv',
                             output_file: str = None) -> bool:
    """
    Esporta i dati delle candidature in un formato compatibile con tracker esterni.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        format_type: Formato di esportazione ('csv', 'json', 'excel')
        output_file: Percorso al file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    if format_type == 'csv':
        result = _generate_csv_report([index], output_file)
        return "Errore" not in result
    else:
        logging.error(f"Formato di esportazione non supportato: {format_type}")
        return False


def set_reminder_for_followup(job_file: str, reminder_date: str = None, 
                            days_from_now: int = 7) -> bool:
    """
    Imposta un promemoria per il follow-up di una candidatura.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        reminder_date: Data del promemoria (formato ISO)
        days_from_now: Giorni da oggi per il promemoria (se reminder_date non è specificato)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Calcola la data del promemoria se non specificata
        if not reminder_date:
            reminder_date = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).isoformat()
        
        # Imposta la data del promemoria
        job_data['Application']['Follow Up Date'] = reminder_date
        
        # Aggiorna le note
        reminder_note = f"Promemoria per follow-up impostato per {reminder_date.split('T')[0] if 'T' in reminder_date else reminder_date}"
        
        if job_data['Application']['Notes']:
            job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        else:
            job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Promemoria per follow-up impostato per {reminder_date} ({job_file})")
        return True
    except Exception as e:
        logging.error(f"Errore nell'impostazione del promemoria per follow-up: {str(e)}")
        return False


def get_due_followups(jobs_index_file: str) -> List[Dict[str, Any]]:
    """
    Ottiene una lista di offerte che necessitano di follow-up.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        
    Returns:
        Lista di offerte che necessitano di follow-up
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        due_followups = []
        today = datetime.datetime.now().date()
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Cerca le offerte che necessitano di follow-up
        for job_index in index:
            job_id = job_index.get('JobId')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Controlla se è necessario un follow-up
            if 'Application' in job_data and job_data['Application'].get('Follow Up Date'):
                followup_date_str = job_data['Application']['Follow Up Date']
                
                # Converte la data in oggetto datetime
                try:
                    if 'T' in followup_date_str:
                        followup_date = datetime.datetime.fromisoformat(followup_date_str).date()
                    else:
                        followup_date = datetime.datetime.strptime(followup_date_str, '%Y-%m-%d').date()
                    
                    # Controlla se la data è oggi o nel passato
                    if followup_date <= today:
                        due_followups.append({
                            'JobId': job_id,
                            'Title': job_data.get('Title'),
                            'Company': job_data.get('Company Name'),
                            'Status': job_data['Application'].get('Status'),
                            'FollowUpDate': followup_date_str,
                            'FilePath': str(job_files[0])
                        })
                except (ValueError, TypeError):
                    continue
        
        # Ordina per data di follow-up
        due_followups.sort(key=lambda x: x.get('FollowUpDate', ''))
        
        return due_followups
    except Exception as e:
        logging.error(f"Errore nell'ottenimento dei follow-up in scadenza: {str(e)}")
        return []


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Gestore del tracciamento delle candidature')
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando per generare un report
    report_parser = subparsers.add_parser('report', help='Genera un report sullo stato delle candidature')
    report_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    report_parser.add_argument('--output', '-o', help='Percorso al file di output')
    report_parser.add_argument('--format', '-f', choices=['markdown', 'html', 'csv'], default='markdown',
                             help='Formato del report')
    
    # Comando per aggiornare lo stato
    status_parser = subparsers.add_parser('update', help='Aggiorna lo stato di una candidatura')
    status_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    status_parser.add_argument('--status', '-s', required=True,
                             choices=['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
                             help='Nuovo stato della candidatura')
    status_parser.add_argument('--notes', '-n', help='Note da aggiungere')
    status_parser.add_argument('--applied-date', '-d', help='Data di candidatura (formato ISO)')
    
    # Comando per impostare un promemoria
    reminder_parser = subparsers.add_parser('reminder', help='Imposta un promemoria per il follow-up')
    reminder_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    reminder_parser.add_argument('--date', '-d', help='Data del promemoria (formato ISO)')
    reminder_parser.add_argument('--days', type=int, default=7, help='Giorni da oggi per il promemoria')
    
    # Comando per ottenere i follow-up in scadenza
    followup_parser = subparsers.add_parser('followups', help='Ottieni le offerte che necessitano di follow-up')
    followup_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    
    args = parser.parse_args()
    
    # Esegui il comando appropriato
    if args.command == 'report':
        report = generate_application_report(args.index_file, args.output, args.format)
        if report and args.format != 'csv' and not args.output:
            print(report)
    elif args.command == 'update':
        success = update_application_status(args.job_file, args.status, args.notes, args.applied_date)
        print(f"{'Aggiornamento completato con successo' if success else 'Errore nell\'aggiornamento'}")
    elif args.command == 'reminder':
        success = set_reminder_for_followup(args.job_file, args.date, args.days)
        print(f"{'Promemoria impostato con successo' if success else 'Errore nell\'impostazione del promemoria'}")
    elif args.command == 'followups':
        due_follow"""
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts[status] = count
        
        # Calcola le date più recenti di attività
        latest_scraped = max([job.get('ScrapedDate', '2000-01-01') for job in index], default='N/A')
        
        applied_jobs = [job for job in index if job.get('Status') != 'Not Applied' and job.get('AppliedDate')]
        latest_applied = max([job.get('AppliedDate', '2000-01-01') for job in applied_jobs], default='N/A')
        
        # Genera il report nel formato richiesto
        if format_type == 'markdown':
            report = _generate_markdown_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'html':
            report = _generate_html_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'csv':
            report = _generate_csv_report(index, output_file)
        else:
            logging.error(f"Formato non supportato: {format_type}")
            return None
        
        # Salva il report se è specificato un file di output
        if output_file and format_type != 'csv':  # Il CSV è già salvato nella funzione
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report salvato in {output_file}")
        
        return report
    except Exception as e:
        logging.error(f"Errore nella generazione del report: {str(e)}")
        return None


def _generate_markdown_report(index: List[Dict[str, Any]], total_jobs: int,
                            status_counts: Dict[str, int], latest_scraped: str,
                            latest_applied: str) -> str:
    """
    Genera un report in formato Markdown.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato Markdown
    """
    # Intestazione del report
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Report delle Candidature di Lavoro

Generato il: {now}

## Statistiche Generali

- **Offerte totali monitorate**: {total_jobs}
- **Ultima offerta scrappata**: {latest_scraped}
- **Ultima candidatura inviata**: {latest_applied}

## Stato delle Candidature

| Stato | Conteggio | Percentuale |
|-------|-----------|-------------|
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            report += f"| {status} | {count} | {percentage:.1f}% |\n"
        else:
            report += f"| {status} | {count} | 0% |\n"
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        report += "\n## Candidature Attive\n\n"
        report += "| Azienda | Titolo | Stato | Data Candidatura |\n"
        report += "|---------|--------|-------|------------------|\n"
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            report += f"| {company} | {title} | {status} | {applied_date} |\n"
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        report += "\n## Nuove Offerte Interessanti\n\n"
        report += "| Azienda | Titolo | Rilevanza | Posizione |\n"
        report += "|---------|--------|-----------|----------|\n"
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            report += f"| {company} | {title} | {relevance} | {location} |\n"
    
    return report


def _generate_html_report(index: List[Dict[str, Any]], total_jobs: int,
                         status_counts: Dict[str, int], latest_scraped: str,
                         latest_applied: str) -> str:
    """
    Genera un report in formato HTML.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato HTML
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Candidature Lavoro</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #2a5885; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2a5885; }}
        .progress-container {{ background-color: #e0e0e0; border-radius: 5px; margin-top: 5px; }}
        .progress-bar {{ background-color: #4CAF50; height: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report delle Candidature di Lavoro</h1>
    <p>Generato il: {now}</p>
    
    <h2>Statistiche Generali</h2>
    <div class="stats">
        <div class="stat-card">
            <div>Offerte Totali</div>
            <div class="stat-value">{total_jobs}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Offerta Scrappata</div>
            <div class="stat-value">{latest_scraped.split('T')[0] if 'T' in latest_scraped else latest_scraped}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Candidatura</div>
            <div class="stat-value">{latest_applied.split('T')[0] if 'T' in latest_applied else latest_applied}</div>
        </div>
    </div>
    
    <h2>Stato delle Candidature</h2>
    <table>
        <tr>
            <th>Stato</th>
            <th>Conteggio</th>
            <th>Percentuale</th>
            <th>Progresso</th>
        </tr>
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {percentage}%;"></div>
                </div>
            </td>
        </tr>"""
        else:
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>0%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%;"></div>
                </div>
            </td>
        </tr>"""
    
    html += """
    </table>
    """
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        html += """
    <h2>Candidature Attive</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Stato</th>
            <th>Data Candidatura</th>
        </tr>
"""
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{status}</td>
            <td>{applied_date}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        html += """
    <h2>Nuove Offerte Interessanti</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Rilevanza</th>
            <th>Posizione</th>
        </tr>
"""
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{relevance}</td>
            <td>{location}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    html += """
</body>
</html>
"""
    
    return html


def _generate_csv_report(index: List[Dict[str, Any]], output_file: str) -> str:
    """
    Genera un report in formato CSV.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        output_file: Percorso al file di output
        
    Returns:
        Messaggio di successo
    """
    if not output_file:
        output_file = f"job_applications_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    
    # Definisci i campi CSV
    fieldnames = [
        'JobId', 'Title', 'Company', 'Location', 'RemoteStatus',
        'DetailURL', 'PostedDate', 'ScrapedDate', 'Status',
        'AppliedDate', 'Priority', 'InterestLevel', 'Relevance'
    ]
    
    # Scrivi il file CSV
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in index:
                # Filtra solo i campi che vogliamo nel CSV
                job_row = {field: job.get(field, '') for field in fieldnames if field in job}
                writer.writerow(job_row)
        
        logging.info(f"File CSV salvato in {output_file}")
        return f"Report CSV generato con successo e salvato in {output_file}"
    except Exception as e:
        logging.error(f"Errore nella creazione del file CSV: {str(e)}")
        return f"Errore nella generazione del report CSV: {str(e)}"


def update_application_status(job_file: str, new_status: str, notes: str = None, 
                            applied_date: str = None) -> bool:
    """
    Aggiorna lo stato della candidatura per un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        new_status: Nuovo stato della candidatura
        notes: Note opzionali da aggiungere
        applied_date: Data di candidatura (se diversa da oggi)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Imposta la data di oggi come predefinita se non specificata
        if not applied_date:
            if new_status == 'Applied' and job_data['Application']['Status'] == 'Not Applied':
                applied_date = datetime.datetime.now().isoformat()
        
        # Aggiorna lo stato della candidatura
        old_status = job_data['Application']['Status']
        job_data['Application']['Status'] = new_status
        
        # Aggiorna i campi relativi alla data in base allo stato
        if new_status == 'Applied' and applied_date:
            job_data['Application']['Applied Date'] = applied_date
        elif new_status == 'Screening':
            job_data['Application']['Response Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Interview':
            job_data['Application']['Interview Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Offer':
            job_data['Application']['Offer Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Rejected':
            job_data['Application']['Rejection Date'] = datetime.datetime.now().isoformat()
        
        # Aggiorna le note se fornite
        if notes:
            if job_data['Application']['Notes']:
                job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato da '{old_status}' a '{new_status}' per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_for_job(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura: {str(e)}")
        return False


def update_index_for_job(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna l'indice per un'offerta specifica.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta dall'URL
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            logging.error("Impossibile estrarre l'ID dell'offerta dai dati")
            return False
        
        # Trova la voce corrispondente nell'indice
        updated = False
        for job_entry in index:
            if job_entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice con i dati dell'offerta
                if 'Application' in job_data:
                    job_entry['Status'] = job_data['Application'].get('Status', 'Not Applied')
                    job_entry['AppliedDate'] = job_data['Application'].get('Applied Date')
                    job_entry['Priority'] = job_data['Application'].get('Priority', 'Medium')
                    job_entry['InterestLevel'] = job_data['Application'].get('Interest Level', 'Medium')
                updated = True
                break
        
        if not updated:
            logging.warning(f"Nessuna voce trovata nell'indice per l'offerta con ID {job_id}")
            return False
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta con ID {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False


def export_to_external_tracker(jobs_index_file: str, format_type: str = 'csv',
                             output_file: str = None) -> bool:
    """
    Esporta i dati delle candidature in un formato compatibile con tracker esterni.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        format_type: Formato di esportazione ('csv', 'json', 'excel')
        output_file: Percorso al file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    if format_type == 'csv':
        result = _generate_csv_report([index], output_file)
        return "Errore" not in result
    else:
        logging.error(f"Formato di esportazione non supportato: {format_type}")
        return False


def set_reminder_for_followup(job_file: str, reminder_date: str = None, 
                            days_from_now: int = 7) -> bool:
    """
    Imposta un promemoria per il follow-up di una candidatura.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        reminder_date: Data del promemoria (formato ISO)
        days_from_now: Giorni da oggi per il promemoria (se reminder_date non è specificato)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Calcola la data del promemoria se non specificata
        if not reminder_date:
            reminder_date = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).isoformat()
        
        # Imposta la data del promemoria
        job_data['Application']['Follow Up Date'] = reminder_date
        
        # Aggiorna le note
        reminder_note = f"Promemoria per follow-up impostato per {reminder_date.split('T')[0] if 'T' in reminder_date else reminder_date}"
        
        if job_data['Application']['Notes']:
            job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        else:
            job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Promemoria per follow-up impostato per {reminder_date} ({job_file})")
        return True
    except Exception as e:
        logging.error(f"Errore nell'impostazione del promemoria per follow-up: {str(e)}")
        return False


def get_due_followups(jobs_index_file: str) -> List[Dict[str, Any]]:
    """
    Ottiene una lista di offerte che necessitano di follow-up.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        
    Returns:
        Lista di offerte che necessitano di follow-up
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        due_followups = []
        today = datetime.datetime.now().date()
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Cerca le offerte che necessitano di follow-up
        for job_index in index:
            job_id = job_index.get('JobId')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Controlla se è necessario un follow-up
            if 'Application' in job_data and job_data['Application'].get('Follow Up Date'):
                followup_date_str = job_data['Application']['Follow Up Date']
                
                # Converte la data in oggetto datetime
                try:
                    if 'T' in followup_date_str:
                        followup_date = datetime.datetime.fromisoformat(followup_date_str).date()
                    else:
                        followup_date = datetime.datetime.strptime(followup_date_str, '%Y-%m-%d').date()
                    
                    # Controlla se la data è oggi o nel passato
                    if followup_date <= today:
                        due_followups.append({
                            'JobId': job_id,
                            'Title': job_data.get('Title'),
                            'Company': job_data.get('Company Name'),
                            'Status': job_data['Application'].get('Status'),
                            'FollowUpDate': followup_date_str,
                            'FilePath': str(job_files[0])
                        })
                except (ValueError, TypeError):
                    continue
        
        # Ordina per data di follow-up
        due_followups.sort(key=lambda x: x.get('FollowUpDate', ''))
        
        return due_followups
    except Exception as e:
        logging.error(f"Errore nell'ottenimento dei follow-up in scadenza: {str(e)}")
        return []


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Gestore del tracciamento delle candidature')
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando per generare un report
    report_parser = subparsers.add_parser('report', help='Genera un report sullo stato delle candidature')
    report_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    report_parser.add_argument('--output', '-o', help='Percorso al file di output')
    report_parser.add_argument('--format', '-f', choices=['markdown', 'html', 'csv'], default='markdown',
                             help='Formato del report')
    
    # Comando per aggiornare lo stato
    status_parser = subparsers.add_parser('update', help='Aggiorna lo stato di una candidatura')
    status_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    status_parser.add_argument('--status', '-s', required=True,
                             choices=['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
                             help='Nuovo stato della candidatura')
    status_parser.add_argument('--notes', '-n', help='Note da aggiungere')
    status_parser.add_argument('--applied-date', '-d', help='Data di candidatura (formato ISO)')
    
    # Comando per impostare un promemoria
    reminder_parser = subparsers.add_parser('reminder', help='Imposta un promemoria per il follow-up')
    reminder_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    reminder_parser.add_argument('--date', '-d', help='Data del promemoria (formato ISO)')
    reminder_parser.add_argument('--days', type=int, default=7, help='Giorni da oggi per il promemoria')
    
    # Comando per ottenere i follow-up in scadenza
    followup_parser = subparsers.add_parser('followups', help='Ottieni le offerte che necessitano di follow-up')
    followup_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    
    args = parser.parse_args()
    
    # Esegui il comando appropriato
    if args.command == 'report':
        report = generate_application_report(args.index_file, args.output, args.format)
        if report and args.format != 'csv' and not args.output:
            print(report)
    elif args.command == 'update':
        success = update_application_status(args.job_file, args.status, args.notes, args.applied_date)
        print(f"{'Aggiornamento completato con successo' if success else 'Errore nell\'aggiornamento'}")
    elif args.command == 'reminder':
        success = set_reminder_for_followup(args.job_file, args.date, args.days)
        print(f"{'Promemoria impostato con successo' if success else 'Errore nell\'impostazione del promemoria'}")
    elif args.command == 'followups':"""
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts[status] = count
        
        # Calcola le date più recenti di attività
        latest_scraped = max([job.get('ScrapedDate', '2000-01-01') for job in index], default='N/A')
        
        applied_jobs = [job for job in index if job.get('Status') != 'Not Applied' and job.get('AppliedDate')]
        latest_applied = max([job.get('AppliedDate', '2000-01-01') for job in applied_jobs], default='N/A')
        
        # Genera il report nel formato richiesto
        if format_type == 'markdown':
            report = _generate_markdown_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'html':
            report = _generate_html_report(index, total_jobs, status_counts, latest_scraped, latest_applied)
        elif format_type == 'csv':
            report = _generate_csv_report(index, output_file)
        else:
            logging.error(f"Formato non supportato: {format_type}")
            return None
        
        # Salva il report se è specificato un file di output
        if output_file and format_type != 'csv':  # Il CSV è già salvato nella funzione
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report salvato in {output_file}")
        
        return report
    except Exception as e:
        logging.error(f"Errore nella generazione del report: {str(e)}")
        return None


def _generate_markdown_report(index: List[Dict[str, Any]], total_jobs: int,
                            status_counts: Dict[str, int], latest_scraped: str,
                            latest_applied: str) -> str:
    """
    Genera un report in formato Markdown.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato Markdown
    """
    # Intestazione del report
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Report delle Candidature di Lavoro

Generato il: {now}

## Statistiche Generali

- **Offerte totali monitorate**: {total_jobs}
- **Ultima offerta scrappata**: {latest_scraped}
- **Ultima candidatura inviata**: {latest_applied}

## Stato delle Candidature

| Stato | Conteggio | Percentuale |
|-------|-----------|-------------|
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            report += f"| {status} | {count} | {percentage:.1f}% |\n"
        else:
            report += f"| {status} | {count} | 0% |\n"
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        report += "\n## Candidature Attive\n\n"
        report += "| Azienda | Titolo | Stato | Data Candidatura |\n"
        report += "|---------|--------|-------|------------------|\n"
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            report += f"| {company} | {title} | {status} | {applied_date} |\n"
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        report += "\n## Nuove Offerte Interessanti\n\n"
        report += "| Azienda | Titolo | Rilevanza | Posizione |\n"
        report += "|---------|--------|-----------|----------|\n"
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            report += f"| {company} | {title} | {relevance} | {location} |\n"
    
    return report


def _generate_html_report(index: List[Dict[str, Any]], total_jobs: int,
                         status_counts: Dict[str, int], latest_scraped: str,
                         latest_applied: str) -> str:
    """
    Genera un report in formato HTML.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        total_jobs: Numero totale di offerte
        status_counts: Conteggi per stato
        latest_scraped: Data più recente di scraping
        latest_applied: Data più recente di candidatura
        
    Returns:
        Report in formato HTML
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Candidature Lavoro</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #2a5885; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2a5885; }}
        .progress-container {{ background-color: #e0e0e0; border-radius: 5px; margin-top: 5px; }}
        .progress-bar {{ background-color: #4CAF50; height: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report delle Candidature di Lavoro</h1>
    <p>Generato il: {now}</p>
    
    <h2>Statistiche Generali</h2>
    <div class="stats">
        <div class="stat-card">
            <div>Offerte Totali</div>
            <div class="stat-value">{total_jobs}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Offerta Scrappata</div>
            <div class="stat-value">{latest_scraped.split('T')[0] if 'T' in latest_scraped else latest_scraped}</div>
        </div>
        <div class="stat-card">
            <div>Ultima Candidatura</div>
            <div class="stat-value">{latest_applied.split('T')[0] if 'T' in latest_applied else latest_applied}</div>
        </div>
    </div>
    
    <h2>Stato delle Candidature</h2>
    <table>
        <tr>
            <th>Stato</th>
            <th>Conteggio</th>
            <th>Percentuale</th>
            <th>Progresso</th>
        </tr>
"""
    
    # Tabella degli stati
    for status, count in status_counts.items():
        if total_jobs > 0:
            percentage = (count / total_jobs) * 100
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {percentage}%;"></div>
                </div>
            </td>
        </tr>"""
        else:
            html += f"""
        <tr>
            <td>{status}</td>
            <td>{count}</td>
            <td>0%</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%;"></div>
                </div>
            </td>
        </tr>"""
    
    html += """
    </table>
    """
    
    # Offerte attive (in processo)
    active_statuses = ['Applied', 'Screening', 'Interview']
    active_jobs = [job for job in index if job.get('Status') in active_statuses]
    
    if active_jobs:
        html += """
    <h2>Candidature Attive</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Stato</th>
            <th>Data Candidatura</th>
        </tr>
"""
        
        for job in sorted(active_jobs, key=lambda x: x.get('AppliedDate', ''), reverse=True):
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            status = job.get('Status', 'N/A')
            applied_date = job.get('AppliedDate', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{status}</td>
            <td>{applied_date}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    # Offerte nuove (non ancora processate)
    new_jobs = [job for job in index if job.get('Status') == 'Not Applied']
    
    if new_jobs:
        top_new_jobs = sorted(new_jobs, key=lambda x: x.get('Relevance', 0), reverse=True)[:10]
        
        html += """
    <h2>Nuove Offerte Interessanti</h2>
    <table>
        <tr>
            <th>Azienda</th>
            <th>Titolo</th>
            <th>Rilevanza</th>
            <th>Posizione</th>
        </tr>
"""
        
        for job in top_new_jobs:
            company = job.get('Company', 'N/A')
            title = job.get('Title', 'N/A')
            relevance = job.get('Relevance', 0)
            location = job.get('Location', 'N/A')
            
            html += f"""
        <tr>
            <td>{company}</td>
            <td>{title}</td>
            <td>{relevance}</td>
            <td>{location}</td>
        </tr>"""
        
        html += """
    </table>
"""
    
    html += """
</body>
</html>
"""
    
    return html


def _generate_csv_report(index: List[Dict[str, Any]], output_file: str) -> str:
    """
    Genera un report in formato CSV.
    
    Args:
        index: Lista di dati dell'indice delle offerte
        output_file: Percorso al file di output
        
    Returns:
        Messaggio di successo
    """
    if not output_file:
        output_file = f"job_applications_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    
    # Definisci i campi CSV
    fieldnames = [
        'JobId', 'Title', 'Company', 'Location', 'RemoteStatus',
        'DetailURL', 'PostedDate', 'ScrapedDate', 'Status',
        'AppliedDate', 'Priority', 'InterestLevel', 'Relevance'
    ]
    
    # Scrivi il file CSV
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in index:
                # Filtra solo i campi che vogliamo nel CSV
                job_row = {field: job.get(field, '') for field in fieldnames if field in job}
                writer.writerow(job_row)
        
        logging.info(f"File CSV salvato in {output_file}")
        return f"Report CSV generato con successo e salvato in {output_file}"
    except Exception as e:
        logging.error(f"Errore nella creazione del file CSV: {str(e)}")
        return f"Errore nella generazione del report CSV: {str(e)}"


def update_application_status(job_file: str, new_status: str, notes: str = None, 
                            applied_date: str = None) -> bool:
    """
    Aggiorna lo stato della candidatura per un'offerta.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        new_status: Nuovo stato della candidatura
        notes: Note opzionali da aggiungere
        applied_date: Data di candidatura (se diversa da oggi)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Imposta la data di oggi come predefinita se non specificata
        if not applied_date:
            if new_status == 'Applied' and job_data['Application']['Status'] == 'Not Applied':
                applied_date = datetime.datetime.now().isoformat()
        
        # Aggiorna lo stato della candidatura
        old_status = job_data['Application']['Status']
        job_data['Application']['Status'] = new_status
        
        # Aggiorna i campi relativi alla data in base allo stato
        if new_status == 'Applied' and applied_date:
            job_data['Application']['Applied Date'] = applied_date
        elif new_status == 'Screening':
            job_data['Application']['Response Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Interview':
            job_data['Application']['Interview Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Offer':
            job_data['Application']['Offer Date'] = datetime.datetime.now().isoformat()
        elif new_status == 'Rejected':
            job_data['Application']['Rejection Date'] = datetime.datetime.now().isoformat()
        
        # Aggiorna le note se fornite
        if notes:
            if job_data['Application']['Notes']:
                job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato da '{old_status}' a '{new_status}' per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_for_job(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura: {str(e)}")
        return False


def update_index_for_job(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna l'indice per un'offerta specifica.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file di indice
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta dall'URL
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            logging.error("Impossibile estrarre l'ID dell'offerta dai dati")
            return False
        
        # Trova la voce corrispondente nell'indice
        updated = False
        for job_entry in index:
            if job_entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice con i dati dell'offerta
                if 'Application' in job_data:
                    job_entry['Status'] = job_data['Application'].get('Status', 'Not Applied')
                    job_entry['AppliedDate'] = job_data['Application'].get('Applied Date')
                    job_entry['Priority'] = job_data['Application'].get('Priority', 'Medium')
                    job_entry['InterestLevel'] = job_data['Application'].get('Interest Level', 'Medium')
                updated = True
                break
        
        if not updated:
            logging.warning(f"Nessuna voce trovata nell'indice per l'offerta con ID {job_id}")
            return False
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta con ID {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False


def export_to_external_tracker(jobs_index_file: str, format_type: str = 'csv',
                             output_file: str = None) -> bool:
    """
    Esporta i dati delle candidature in un formato compatibile con tracker esterni.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        format_type: Formato di esportazione ('csv', 'json', 'excel')
        output_file: Percorso al file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    if format_type == 'csv':
        result = _generate_csv_report([index], output_file)
        return "Errore" not in result
    else:
        logging.error(f"Formato di esportazione non supportato: {format_type}")
        return False


def set_reminder_for_followup(job_file: str, reminder_date: str = None, 
                            days_from_now: int = 7) -> bool:
    """
    Imposta un promemoria per il follow-up di una candidatura.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        reminder_date: Data del promemoria (formato ISO)
        days_from_now: Giorni da oggi per il promemoria (se reminder_date non è specificato)
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file dell'offerta
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Assicurati che la sezione Application esista
        if 'Application' not in job_data:
            from linkedin_job_scraper.models import enrich_job_data_for_application
            job_data = enrich_job_data_for_application(job_data)
        
        # Calcola la data del promemoria se non specificata
        if not reminder_date:
            reminder_date = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).isoformat()
        
        # Imposta la data del promemoria
        job_data['Application']['Follow Up Date'] = reminder_date
        
        # Aggiorna le note
        reminder_note = f"Promemoria per follow-up impostato per {reminder_date.split('T')[0] if 'T' in reminder_date else reminder_date}"
        
        if job_data['Application']['Notes']:
            job_data['Application']['Notes'] += f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        else:
            job_data['Application']['Notes'] = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {reminder_note}"
        
        # Salva il file aggiornato
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Promemoria per follow-up impostato per {reminder_date} ({job_file})")
        return True
    except Exception as e:
        logging.error(f"Errore nell'impostazione del promemoria per follow-up: {str(e)}")
        return False


def get_due_followups(jobs_index_file: str) -> List[Dict[str, Any]]:
    """
    Ottiene una lista di offerte che necessitano di follow-up.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        
    Returns:
        Lista di offerte che necessitano di follow-up
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        due_followups = []
        today = datetime.datetime.now().date()
        
        # Directory di base per i file delle offerte
        base_dir = os.path.dirname(jobs_index_file)
        
        # Cerca le offerte che necessitano di follow-up
        for job_index in index:
            job_id = job_index.get('JobId')
            
            # Cerca il file dell'offerta corrispondente
            job_files = list(Path(base_dir).glob(f"{job_id}*.json"))
            if not job_files:
                continue
                
            # Leggi il file dell'offerta
            with open(job_files[0], 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Controlla se è necessario un follow-up
            if 'Application' in job_data and job_data['Application'].get('Follow Up Date'):
                followup_date_str = job_data['Application']['Follow Up Date']
                
                # Converte la data in oggetto datetime
                try:
                    if 'T' in followup_date_str:
                        followup_date = datetime.datetime.fromisoformat(followup_date_str).date()
                    else:
                        followup_date = datetime.datetime.strptime(followup_date_str, '%Y-%m-%d').date()
                    
                    # Controlla se la data è oggi o nel passato
                    if followup_date <= today:
                        due_followups.append({
                            'JobId': job_id,
                            'Title': job_data.get('Title'),
                            'Company': job_data.get('Company Name'),
                            'Status': job_data['Application'].get('Status'),
                            'FollowUpDate': followup_date_str,
                            'FilePath': str(job_files[0])
                        })
                except (ValueError, TypeError):
                    continue
        
        # Ordina per data di follow-up
        due_followups.sort(key=lambda x: x.get('FollowUpDate', ''))
        
        return due_followups
    except Exception as e:
        logging.error(f"Errore nell'ottenimento dei follow-up in scadenza: {str(e)}")
        return []


if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parser degli argomenti
    parser = argparse.ArgumentParser(description='Gestore del tracciamento delle candidature')
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando per generare un report
    report_parser = subparsers.add_parser('report', help='Genera un report sullo stato delle candidature')
    report_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    report_parser.add_argument('--output', '-o', help='Percorso al file di output')
    report_parser.add_argument('--format', '-f', choices=['markdown', 'html', 'csv'], default='markdown',
                             help='Formato del report')
    
    # Comando per aggiornare lo stato
    status_parser = subparsers.add_parser('update', help='Aggiorna lo stato di una candidatura')
    status_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    status_parser.add_argument('--status', '-s', required=True,
                             choices=['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
                             help='Nuovo stato della candidatura')
    status_parser.add_argument('--notes', '-n', help='Note da aggiungere')
    status_parser.add_argument('--applied-date', '-d', help='Data di candidatura (formato ISO)')
    
    # Comando per impostare un promemoria
    reminder_parser = subparsers.add_parser('reminder', help='Imposta un promemoria per il follow-up')
    reminder_parser.add_argument('job_file', help='Percorso al file JSON dell\'offerta')
    reminder_parser.add_argument('--date', '-d', help='Data del promemoria (formato ISO)')
    reminder_parser.add_argument('--days', type=int, default=7, help='Giorni da oggi per il promemoria')
    
    # Comando per ottenere i follow-up in scadenza
    followup_parser = subparsers.add_parser('followups', help='Ottieni le offerte che necessitano di follow-up')
    followup_parser.add_argument('index_file', help='Percorso al file di indice delle offerte')
    
    args = parser.parse_args()
    
    # Esegui il comando appropriato
    if args.command == 'report':
        report = generate_application_report(args.index_file, args.output, args.format)
        if report and args.format != 'csv' and not args.output:
            print(report)
    elif args.command == 'update':
        success = update_application_status(args.job_file, args.status, args.notes, args.applied_date)
        print(f"{'Aggiornamento completato con successo' if success else 'Errore nell\'aggiornamento'}")
    elif args.command == 'reminder':
        success = set_reminder_for_followup(args.job_file, args.date, args.days)
        print(f"{'Promemoria impostato con successo' if success else 'Errore nell\'impostazione del promemoria'}")
    elif args.command == 'followups':"""
Funzioni per l'integrazione con sistemi di tracciamento delle candidature.
Gestisce l'aggiornamento dello stato delle candidature e la sincronizzazione con altri sistemi.
"""

import os
import json
import logging
import datetime
import csv
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from linkedin_job_scraper.utils import sanitize_filename


def generate_application_report(jobs_index_file: str, output_file: str = None,
                              format_type: str = 'markdown') -> Optional[str]:
    """
    Genera un report sullo stato delle candidature.
    
    Args:
        jobs_index_file: Percorso al file di indice delle offerte
        output_file: Percorso al file di output (opzionale)
        format_type: Formato del report ('markdown', 'html', 'csv')
        
    Returns:
        Testo del report se con successo, None altrimenti
    """
    try:
        # Leggi il file di indice
        with open(jobs_index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if not index:
            logging.warning("Nessuna offerta trovata nell'indice")
            return None
        
        # Calcola statistiche
        total_jobs = len(index)
        status_counts = {}
        status_list = ['Not Applied', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
        
        for status in status_list:
            count = sum(1 for job in index if job.get('Status') == status)
            status_counts