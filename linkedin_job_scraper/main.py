#!/usr/bin/env python3
"""
Punto di ingresso principale per LinkedIn Job Scraper.
Consente l'esecuzione del pacchetto direttamente con python -m linkedin_job_scraper
"""

import sys
import os
import argparse
import json
from typing import List, Dict, Any, Tuple
import logging

# Aggiungi la directory principale al path per consentire l'importazione di exporters
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .config import load_config
from .cli import configure_argument_parser
from .scraper import process_search_results, scrape_linkedin_job
from .utils import build_search_url, setup_logging

# Ora importa da exporters sarà possibile
try:
    from exporters.json_exporter import save_job_data_to_json, export_individual_job_files, create_jobs_index
except ImportError:
    # Definisci funzioni di fallback in caso exporters non sia disponibile
    def save_job_data_to_json(job_data, output_file):
        """Funzione di fallback per salvare i dati dell'offerta in un file JSON."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([job_data], f, indent=2, ensure_ascii=False)
            logging.info(f"Dati dell'offerta salvati in {output_file}")
            return True
        except Exception as e:
            logging.error(f"Errore nel salvataggio dei dati dell'offerta in {output_file}: {str(e)}")
            return False
    
    def export_individual_job_files(jobs_data, output_dir, enrich=True):
        """Funzione di fallback per esportare file individuali."""
        logging.info("USANDO LA VERSIONE DI export_individual_job_files DA main.py")
        os.makedirs(output_dir, exist_ok=True)
        exported_files = []
        for job in jobs_data:
            job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
            if not job_id:
                continue
            
            company_name = job.get('Company Name', 'Unknown').replace(' ', '_')
            job_title = job.get('Title', 'Unknown').replace(' ', '_')
            filename = f"{job_id}_{company_name}_{job_title}.json"[:100]
            
            file_path = os.path.join(output_dir, filename)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(job, f, indent=2, ensure_ascii=False)
                logging.info(f"Offerta {job_id} esportata in {file_path}")
                exported_files.append(file_path)
            except Exception as e:
                logging.error(f"Errore nell'esportazione dell'offerta {job_id}: {str(e)}")
        return exported_files
    
    def create_jobs_index(jobs_data, output_file):
        """Funzione di fallback per creare l'indice delle offerte."""
        index = []
        for job in jobs_data:
            job_id = job.get('Detail URL', '').split('/')[-1].split('?')[0]
            if not job_id:
                continue
                
            index_entry = {
                "JobId": job_id,
                "Title": job.get('Title'),
                "Company": job.get('Company Name'),
                "Location": job.get('Location'),
                "RemoteStatus": "Remote" if "remote" in job.get('Location', '').lower() else "Not Specified",
                "DetailURL": job.get('Detail URL'),
                "PostedDate": job.get('Created At'),
                "ScrapedDate": job.get('ScrapedAt'),
                "Status": "Not Applied",
                "Priority": "Medium"
            }
            
            # Aggiungi punteggio di rilevanza se disponibile
            if 'Relevance' in job:
                index_entry["Relevance"] = job['Relevance'].get('Score', 0)
            else:
                index_entry["Relevance"] = 0
            
            index.append(index_entry)
        
        # Ordina per punteggio di rilevanza (più alto al più basso)
        index.sort(key=lambda x: x.get('Relevance', 0), reverse=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            logging.info(f"Indice delle offerte creato in {output_file}")
            return True
        except Exception as e:
            logging.error(f"Errore nella creazione dell'indice delle offerte: {str(e)}")
            return False


def main():
    """
    Funzione principale del programma.
    Gestisce il parsing degli argomenti da linea di comando e avvia il processo di scraping.
    """
    try:
        # Carica configurazioni da .env se presente
        config = load_config()
        
        # Configura logging
        logger = setup_logging(config.get('LOG_LEVEL', 'INFO'), config.get('LOG_FILE'))
        
        # Configura il parser degli argomenti
        parser = configure_argument_parser(config)
        args = parser.parse_args()
        
        # Se keywords e location sono forniti, costruisce un URL di ricerca
        if args.keywords and args.location:
            url = build_search_url(
                keywords=args.keywords,
                location=args.location,
                remote=args.remote,
                hybrid=args.hybrid,
                easy_apply=args.easy_apply,
                recent=args.recent,
                seniority=args.seniority,
                use_guest_api=args.use_guest_api
            )
            logger.info(f"URL di ricerca generato: {url}")
        else:
            url = args.url
        
        if not url:
            logger.error("È necessario fornire un URL o specificare keywords e location")
            parser.print_help()
            sys.exit(1)
        
        # Determina se l'URL è un'offerta singola o una ricerca
        if "/jobs/view/" in url or "currentJobId=" in url:
            # Offerta di lavoro singola
            logger.info(f"Scraping dell'offerta singola: {url}")
            job_data = scrape_linkedin_job(url)
            
            if not job_data:
                logger.error("Impossibile effettuare lo scraping dei dati dell'offerta")
                sys.exit(1)
            
            # Salva i dati dell'offerta in un file JSON
            success = save_job_data_to_json(job_data, args.output_file)
            
            # Se richiesto, esporta anche come file individuale
            if args.export_individual and success:
                export_individual_job_files([job_data], args.output_dir, enrich=True)
                
            sys.exit(0 if success else 1)
        else:
            # Risultati di ricerca
            logger.info(f"Elaborazione dei risultati di ricerca: {url}")
            success, all_jobs_data = process_search_results(
                url, 
                args.output_file,
                max_jobs=args.max_jobs
            )
            
            # Se richiesto, esporta file individuali e crea indice
            if args.export_individual and success and all_jobs_data:
                export_individual_job_files(all_jobs_data, args.output_dir, enrich=True)
                create_jobs_index(all_jobs_data, f"{args.output_dir}/jobs_index.json")
            
            # Pulisci i file di debug
            from .scraper import cleanup_debug_files
            cleanup_debug_files(keep_last_n=5)
                
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.info("Operazione interrotta dall'utente")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Errore imprevisto: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
            
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()