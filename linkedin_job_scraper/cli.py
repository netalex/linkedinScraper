"""
Interfaccia a riga di comando per LinkedIn Job Scraper.
Gestisce l'analisi degli argomenti da linea di comando e fornisce help contestuali.
"""

import argparse
from typing import Dict, Any


def configure_argument_parser(config: Dict[str, Any] = None) -> argparse.ArgumentParser:
    """
    Configura il parser degli argomenti da linea di comando.
    
    Args:
        config: Configurazione opzionale con valori predefiniti
        
    Returns:
        Parser degli argomenti configurato
    """
    config = config or {}
    
    # Crea il parser principale
    parser = argparse.ArgumentParser(
        description='LinkedIn Job Scraper - Uno strumento per automatizzare la ricerca di lavoro',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Opzioni di base
    parser.add_argument('url', nargs='?', default=None,
                        help='URL di una singola offerta di lavoro o di una ricerca di LinkedIn')
    parser.add_argument('--output-file', '-o', default='linkedin_jobs.json',
                        help='Percorso del file di output JSON')
    
    # Opzioni per la ricerca
    search_group = parser.add_argument_group('Opzioni di ricerca')
    search_group.add_argument('--keywords', '-k', default=config.get('DEFAULT_KEYWORDS'),
                             help='Parole chiave per la ricerca di lavoro')
    search_group.add_argument('--location', '-l', default=config.get('DEFAULT_LOCATION'),
                             help='Posizione geografica per la ricerca')
    search_group.add_argument('--remote', '-r', action='store_true',
                             help='Filtra per lavori remoti')
    search_group.add_argument('--hybrid', action='store_true',
                             help='Filtra per lavori ibridi')
    search_group.add_argument('--easy-apply', '-e', action='store_true',
                             help='Filtra per lavori con Easy Apply')
    search_group.add_argument('--recent', action='store_true',
                             help='Filtra per lavori pubblicati nell\'ultima settimana')
    search_group.add_argument('--seniority', choices=['entry', 'associate', 'mid-senior', 'director'],
                             nargs='+', help='Filtra per livello di anzianità')
    search_group.add_argument('--use-guest-api', type=lambda x: (str(x).lower() == 'true'), 
                             default=False,
                             help='Utilizza l\'API guest di LinkedIn per la ricerca (true/false)')
    
    # Opzioni per i limiti e i ritardi
    limits_group = parser.add_argument_group('Limiti e ritardi')
    limits_group.add_argument('--max-jobs', '-m', type=int, default=config.get('MAX_JOBS_TO_SCRAPE', 25),
                             help='Numero massimo di offerte di lavoro da scrapare')
    limits_group.add_argument('--min-delay', type=float, default=config.get('MIN_DELAY', 2),
                             help='Ritardo minimo tra le richieste (secondi)')
    limits_group.add_argument('--max-delay', type=float, default=config.get('MAX_DELAY', 5),
                             help='Ritardo massimo tra le richieste (secondi)')
    limits_group.add_argument('--max-retries', type=int, default=config.get('MAX_RETRIES', 3),
                             help='Numero massimo di tentativi per richiesta')
    
    # Opzioni per l'esportazione
    export_group = parser.add_argument_group('Opzioni di esportazione')
    export_group.add_argument('--export-individual', action='store_true',
                             help='Esporta file JSON individuali per ogni offerta')
    export_group.add_argument('--output-dir', default=config.get('OUTPUT_DIR', 'job_files'),
                             help='Directory per i file delle offerte individuali')
    export_group.add_argument('--enrich-data', action='store_true', default=True,
                             help='Arricchisci i dati con campi per il tracciamento delle candidature')
    
    # Opzioni avanzate
    advanced_group = parser.add_argument_group('Opzioni avanzate')
    advanced_group.add_argument('--use-proxy', action='store_true', default=config.get('USE_PROXY', False),
                               help='Utilizza un proxy per le richieste')
    advanced_group.add_argument('--proxy-url', default=config.get('PROXY_URL'),
                               help='URL del proxy (formato: http://user:pass@host:port)')
    advanced_group.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                               default=config.get('LOG_LEVEL', 'INFO'),
                               help='Livello di dettaglio dei log')
    advanced_group.add_argument('--log-file', default=config.get('LOG_FILE'),
                               help='Percorso del file di log')
    
    return parser
