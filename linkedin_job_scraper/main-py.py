#!/usr/bin/env python3
"""
Punto di ingresso principale per LinkedIn Job Scraper.
Consente l'esecuzione del pacchetto direttamente con python -m linkedin_job_scraper
"""

import sys
import argparse
from typing import List

from .config import load_config
from .cli import configure_argument_parser
from .scraper import process_search_results, scrape_linkedin_job
from .utils import build_search_url, setup_logging
from exporters.json_exporter import save_job_data_to_json, export_individual_job_files, create_jobs_index


def main():
    """
    Funzione principale del programma.
    Gestisce il parsing degli argomenti da linea di comando e avvia il processo di scraping.
    """
    # Carica configurazioni da .env se presente
    config = load_config()
    
    # Configura logging
    logger = setup_logging()
    
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
            
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
