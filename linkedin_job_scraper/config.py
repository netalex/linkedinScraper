"""
Gestione della configurazione per LinkedIn Job Scraper.
Carica le impostazioni da file .env e definisce valori predefiniti.
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv


# Lista di user agent per rotazione per evitare il rilevamento
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]

# Configurazioni predefinite
DEFAULT_CONFIG = {
    "OUTPUT_DIR": "job_files",
    "INDEX_FILE": "jobs_index.json",
    "MAX_JOBS_TO_SCRAPE": 100,
    "MIN_DELAY": 2,
    "MAX_DELAY": 5,
    "MAX_RETRIES": 3,
    "DEFAULT_LOCATION": "Italy",
    "DEFAULT_KEYWORDS": "front end developer OR angular developer OR react developer",
    "USE_PROXY": False,
    "PROXY_URL": None,
    "LOG_LEVEL": "INFO",
    "LOG_FILE": None,
    "MAX_EMPTY_PAGES": 3,
}


def load_config() -> Dict[str, Any]:
    """
    Carica la configurazione combinando .env e valori predefiniti.
    
    Returns:
        Dizionario con tutte le configurazioni
    """
    # Cerca il file .env nella directory corrente e in quelle superiori
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)
    
    # Combina le configurazioni predefinite con quelle dell'ambiente
    config = DEFAULT_CONFIG.copy()
    
    # Sovrascrivi con i valori dell'ambiente, convertendo i tipi di dati
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            # Converti i valori in base al tipo nel dizionario predefinito
            if isinstance(config[key], bool):
                config[key] = env_value.lower() in ('true', 'yes', '1', 'y')
            elif isinstance(config[key], int):
                try:
                    config[key] = int(env_value)
                except ValueError:
                    logging.warning(f"Impossibile convertire {key}={env_value} in intero. Uso il valore predefinito {config[key]}")
            else:
                config[key] = env_value
    
    return config


def find_dotenv() -> str:
    """
    Cerca il file .env nella directory corrente e in quelle superiori.
    
    Returns:
        Percorso del file .env se trovato, altrimenti stringa vuota
    """
    current_dir = Path.cwd()
    
    # Cerca fino a 3 livelli superiori
    for _ in range(4):
        env_path = current_dir / '.env'
        if env_path.exists():
            return str(env_path)
        
        # Sali di un livello
        parent_dir = current_dir.parent
        if parent_dir == current_dir:  # Siamo alla root
            break
        current_dir = parent_dir
    
    return ""
