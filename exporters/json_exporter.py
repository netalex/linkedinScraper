"""
Funzioni per l'esportazione dei dati in formato JSON.
Gestisce il salvataggio di dati su file, la creazione di file individuali e la generazione di indici.
"""

import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from linkedin_job_scraper.models import validate_job_data, enrich_job_data_for_application
from linkedin_job_scraper.utils import sanitize_filename


def save_job_data_to_json(job_data: Dict[str, Any], output_file: str) -> bool:
    """
    Salva i dati di un'offerta in un file JSON.
    
    Args:
        job_data: Dati dell'offerta da salvare
        output_file: Percorso del file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Crea la directory di output se non esiste
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Validate job data before saving
        from linkedin_job_scraper.models import validate_job_data
        if not validate_job_data(job_data):
            logging.error("Job data failed validation, not saving to file")
            return False
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([job_data], f, indent=2, ensure_ascii=False)
        
        logging.info(f"Dati dell'offerta salvati in {output_file}")
        return True
    except Exception as e:
        logging.error(f"Errore nel salvataggio dei dati dell'offerta in {output_file}: {str(e)}")
        return False


def save_jobs_data_to_json(jobs_data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Salva i dati di più offerte in un file JSON.
    
    Args:
        jobs_data: Lista di dati delle offerte da salvare
        output_file: Percorso del file di output
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Crea la directory di output se non esiste
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Dati di {len(jobs_data)} offerte salvati in {output_file}")
        return True
    except Exception as e:
        logging.error(f"Errore nel salvataggio dei dati delle offerte in {output_file}: {str(e)}")
        return False


def export_individual_job_files(jobs_data: List[Dict[str, Any]], output_dir: str = 'job_files', 
                               enrich: bool = True) -> List[str]:
    """
    Esporta ogni offerta come file JSON individuale.
    
    Args:
        jobs_data: Lista di dizionari di dati delle offerte
        output_dir: Directory per salvare i file individuali
        enrich: Indica se arricchire i dati con campi per il tracciamento delle candidature
        
    Returns:
        Lista di percorsi dei file esportati
    """
    logging.info(f"USANDO LA VERSIONE DI export_individual_job_files DA json_exporter.py")
    logging.info(f"Esportazione di {len(jobs_data)} job files nella directory: {output_dir}")
    
    # Crea la directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)
    
    # IMPORTANTE: Crea un dizionario con job_id -> created_at dai dati originali
    # poiché il campo è presente solo nei risultati di ricerca di gruppo
    original_created_at = {}
    for job in jobs_data:
        job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
        if job_id and job.get('Created At'):
            original_created_at[job_id] = job['Created At']
    
    exported_files = []
    
    for job in jobs_data:
        # Estrai l'ID dell'offerta dall'URL
        job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            continue
            
        # IMPORTANTE: Preserva created_at prima dell'arricchimento
        created_at = job.get('Created At')
        if not created_at and job_id in original_created_at:
            created_at = original_created_at[job_id]
            logging.info(f"Preservata data di creazione originale per job {job_id}: {created_at}")
        
        # Arricchisci i dati se richiesto
        if enrich and 'Application' not in job:
            job = enrich_job_data_for_application(job)
        
        # IMPORTANTE: Ripristina created_at dopo l'arricchimento
        if created_at:
            job['Created At'] = created_at
        elif not job.get('Created At'):
            # Fallback: usa data corrente meno 7 giorni
            one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            job['Created At'] = one_week_ago
            logging.info(f"Usata data fallback per job {job_id}: -{one_week_ago}")
        
        # Crea un nome di file sanitizzato
        company_name = sanitize_filename(job.get('Company Name', 'Unknown'))
        job_title = sanitize_filename(job.get('Title', 'Unknown'))
        
        filename = f"{job_id}_{company_name}_{job_title}.json"
        filename = re.sub(r'\s+', '_', filename)[:100]  # Limita lunghezza
        
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job, f, indent=2, ensure_ascii=False)
            logging.info(f"Offerta {job_id} esportata in {file_path}")
            exported_files.append(file_path)
        except Exception as e:
            logging.error(f"Errore nell'esportazione dell'offerta {job_id}: {str(e)}")
    
    return exported_files


def create_jobs_index(jobs_data: List[Dict[str, Any]], output_file: str = 'jobs_index.json') -> bool:
    """
    Crea un indice di tutte le offerte scrappate.
    
    Args:
        jobs_data: Lista di dizionari di dati delle offerte
        output_file: Percorso del file di output per l'indice
        
    Returns:
        True se con successo, False altrimenti
    """
    index = []
    
    # Analogamente, crea un dizionario con job_id -> created_at
    original_created_at = {}
    for job in jobs_data:
        job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
        if job_id and job.get('Created At'):
            original_created_at[job_id] = job['Created At']
    
    for job in jobs_data:
        # Estrai l'ID dell'offerta dall'URL
        job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            continue
            
        # Usa created_at dal job o dal dizionario originale
        created_at = job.get('Created At')
        if not created_at and job_id in original_created_at:
            created_at = original_created_at[job_id]
        elif not created_at:
            # Fallback: usa data corrente meno 7 giorni
            one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            created_at = one_week_ago
        
        # Crea una voce di indice con informazioni essenziali
        index_entry = {
            "JobId": job_id,
            "Title": job.get('Title'),
            "Company": job.get('Company Name'),
            "Location": job.get('Location'),
            "RemoteStatus": "Remote" if "remote" in job.get('Location', '').lower() else "Not Specified",
            "DetailURL": job.get('Detail URL'),
            "PostedDate": job.get('Created At'),
            "ScrapedDate": job.get('ScrapedAt')
        }
        
        # Aggiungi informazioni sullo stato della candidatura se disponibili
        if 'Application' in job:
            index_entry["Status"] = job['Application'].get('Status', 'Not Applied')
            index_entry["AppliedDate"] = job['Application'].get('Applied Date')
            index_entry["Priority"] = job['Application'].get('Priority', 'Medium')
            index_entry["InterestLevel"] = job['Application'].get('Interest Level', 'Medium')
        else:
            index_entry["Status"] = "Not Applied"
            index_entry["Priority"] = "Medium"
        
        # Aggiungi punteggio di rilevanza se disponibile
        if 'Relevance' in job:
            index_entry["Relevance"] = job['Relevance'].get('Score', 0)
            index_entry["KeywordMatches"] = sum(1 for keyword in job['Relevance'].get('Keywords', [])
                                              if keyword.lower() in job.get('Title', '').lower() or
                                                 keyword.lower() in job.get('Description', '').lower())
        else:
            index_entry["Relevance"] = 0
        
        index.append(index_entry)
    
    # Ordina per punteggio di rilevanza (più alto al più basso)
    index.sort(key=lambda x: x.get('Relevance', 0), reverse=True)
    
    # Crea la directory di output se non esiste
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        logging.info(f"Indice delle offerte creato in {output_file}")
        return True
    except Exception as e:
        logging.error(f"Errore nella creazione dell'indice delle offerte: {str(e)}")
        return False


def update_job_application_status(job_file: str, status_update: Dict[str, Any]) -> bool:
    """
    Aggiorna lo stato della candidatura in un file di offerta esistente.
    
    Args:
        job_file: Percorso al file JSON dell'offerta
        status_update: Dizionario con i campi da aggiornare
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi il file esistente
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Verifica se il campo Application esiste e crealo se necessario
        if 'Application' not in job_data:
            job_data = enrich_job_data_for_application(job_data)
        
        # Aggiorna i campi specificati
        for key, value in status_update.items():
            if key in job_data['Application']:
                job_data['Application'][key] = value
        
        # Salva le modifiche
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Stato della candidatura aggiornato per {job_file}")
        
        # Aggiorna anche l'indice se esiste nella stessa directory
        job_dir = os.path.dirname(job_file)
        index_file = os.path.join(job_dir, 'jobs_index.json')
        
        if os.path.exists(index_file):
            update_index_status(index_file, job_data)
        
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dello stato della candidatura in {job_file}: {str(e)}")
        return False


def update_index_status(index_file: str, job_data: Dict[str, Any]) -> bool:
    """
    Aggiorna lo stato di un'offerta nell'indice.
    
    Args:
        index_file: Percorso al file di indice
        job_data: Dati dell'offerta aggiornati
        
    Returns:
        True se con successo, False altrimenti
    """
    try:
        # Leggi l'indice esistente
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Estrai l'ID dell'offerta
        job_id = job_data.get('Detail URL', '').split('/')[-1].split('?')[0]
        if not job_id:
            return False
        
        # Trova la voce corrispondente nell'indice
        for entry in index:
            if entry.get('JobId') == job_id:
                # Aggiorna i campi dell'indice
                if 'Application' in job_data:
                    entry["Status"] = job_data['Application'].get('Status', 'Not Applied')
                    entry["AppliedDate"] = job_data['Application'].get('Applied Date')
                    entry["Priority"] = job_data['Application'].get('Priority', 'Medium')
                    entry["InterestLevel"] = job_data['Application'].get('Interest Level', 'Medium')
                break
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Indice aggiornato per l'offerta {job_id}")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dell'indice: {str(e)}")
        return False
