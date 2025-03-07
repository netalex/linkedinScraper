"""
Utilità varie per LinkedIn Job Scraper.
Funzioni di supporto per richieste HTTP, logging, generazione di URL e altre operazioni comuni.
"""

import os
import sys
import time
import random
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, quote
import requests
from pathlib import Path

from .config import USER_AGENTS


def get_random_user_agent() -> str:
    """
    Restituisce uno user agent casuale dalla lista per evitare il rilevamento.
    
    Returns:
        User agent casuale
    """
    return random.choice(USER_AGENTS)


def get_request_headers(referer: str = None) -> Dict[str, str]:
    """
    Genera header di richiesta che imitano un browser reale.
    
    Args:
        referer: URL opzionale da utilizzare come referer
        
    Returns:
        Dizionario di header HTTP
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'DNT': '1',  # Do Not Track
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    if referer:
        headers['Referer'] = referer
    
    return headers


def make_request_with_backoff(url: str, headers: Dict[str, str] = None, 
                             max_retries: int = 3, min_delay: int = 1, 
                             max_delay: int = 3, proxy_url: str = None) -> Optional[str]:
    """
    Effettua una richiesta HTTP con backoff esponenziale per i tentativi.
    
    Args:
        url: URL della richiesta
        headers: Header della richiesta opzionali
        max_retries: Numero massimo di tentativi di riprova
        min_delay: Ritardo minimo tra le richieste (secondi)
        max_delay: Ritardo massimo tra le richieste (secondi)
        proxy_url: URL del proxy opzionale
        
    Returns:
        Testo della risposta se con successo, None altrimenti
    """
    headers = headers or get_request_headers()
    proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None
    
    for attempt in range(max_retries):
        try:
            # Ritardo casuale tra le richieste
            # Aumenta il ritardo per i tentativi successivi
            delay = random.uniform(min_delay, max_delay) * (2 ** attempt)
            time.sleep(delay)
            
            logging.info(f"Richiesta a {url}")
            response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            
            # Controlla se la richiesta ha avuto successo
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                logging.error(f"Accesso vietato (403): {url}")
                # Interrompi il ciclo se siamo esplicitamente vietati
                break
            elif response.status_code == 429:
                logging.warning(f"Troppe richieste (429): {url}. Riprovo dopo un ritardo più lungo...")
                # Attendi più a lungo prima del prossimo tentativo
                time.sleep(10 * (2 ** attempt))
                continue
            else:
                logging.error(f"Richiesta fallita con codice {response.status_code}: {url}")
                # Attendi prima di riprovare
                time.sleep(5)
                continue
                
        except Exception as e:
            logging.error(f"Errore durante la richiesta a {url}: {str(e)}")
            time.sleep(5)
            continue
    
    return None


def extract_job_id_from_url(url: str) -> Optional[str]:
    """
    Estrae l'ID dell'offerta di lavoro da un URL di LinkedIn.
    
    Args:
        url: URL dell'offerta di lavoro di LinkedIn
        
    Returns:
        ID dell'offerta se trovato, None altrimenti
    """
    # Vari pattern di URL per le offerte di lavoro di LinkedIn
    patterns = [
        r"linkedin\.com/jobs/view/(\d+)",  # https://www.linkedin.com/jobs/view/3887695775/
        r"currentJobId=(\d+)",  # Parametro URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Controlla i parametri URL
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # Controlla i parametri jobId/currentJobId
    for param in ['jobId', 'currentJobId']:
        if param in query_params and query_params[param]:
            return query_params[param][0]
    
    return None


def build_search_url(keywords: str, location: str, remote: bool = False, 
                   hybrid: bool = False, easy_apply: bool = False, 
                   recent: bool = False, seniority: List[str] = None,
                   use_guest_api: bool = True) -> str:
    """
    Costruisce un URL di ricerca di lavoro di LinkedIn con i parametri specificati.
    
    Args:
        keywords: Parole chiave per la ricerca
        location: Posizione del lavoro
        remote: Filtra per lavori remoti
        hybrid: Filtra per lavori ibridi
        easy_apply: Filtra per lavori con Easy Apply
        recent: Filtra per lavori pubblicati nell'ultima settimana
        seniority: Lista di livelli di anzianità (entry, associate, mid-senior, director)
        use_guest_api: Utilizza l'API guest di LinkedIn invece della pagina di ricerca standard
        
    Returns:
        URL di ricerca di lavoro di LinkedIn
    """
    # URL base
    if use_guest_api:
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    else:
        base_url = "https://www.linkedin.com/jobs/search"
    
    # Costruisce i parametri della query
    params = {
        "keywords": keywords,
        "location": location,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "position": 1,
        "pageNum": 0
    }
    
    # Aggiunge filtri
    if remote:
        params["f_WT"] = 2  # Filtro remoto
    
    if hybrid:
        params["f_WT"] = 3  # Filtro ibrido
    
    if easy_apply:
        params["f_AL"] = "true"  # Filtro Easy Apply
    
    if recent:
        params["f_TPR"] = "r604800"  # Ultima settimana
    
    # Aggiunge filtri di anzianità
    if seniority:
        seniority_codes = []
        for level in seniority:
            if level.lower() == "entry":
                seniority_codes.append(2)
            elif level.lower() == "associate":
                seniority_codes.append(3)
            elif level.lower() == "mid-senior":
                seniority_codes.append(4)
            elif level.lower() == "director":
                seniority_codes.append(5)
        
        if seniority_codes:
            params["f_E"] = ','.join(map(str, seniority_codes))
    
    # Codifica i parametri e costruisce l'URL
    return f"{base_url}?{urlencode(params, quote_via=quote)}"


def setup_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    Configura il sistema di logging.
    
    Args:
        log_level: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Percorso del file di log opzionale
    
    Returns:
        Oggetto logger configurato
    """
    # Converti stringa del livello di log in costante di logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Configurazione base
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Se è specificato un file di log, assicurati che la cartella esista
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # Configura il logging
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.NullHandler(),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger()


def sanitize_filename(filename: str) -> str:
    """
    Rende sicuro un nome di file rimuovendo caratteri non validi.
    
    Args:
        filename: Nome di file da rendere sicuro
        
    Returns:
        Nome di file sicuro
    """
    # Rimuovi caratteri non validi
    s = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Sostituisci spazi con underscore
    s = re.sub(r'\s+', '_', s)
    # Limita la lunghezza
    return s[:100]


def get_timestamp() -> str:
    """
    Restituisce un timestamp formattato per l'uso nei nomi di file.
    
    Returns:
        Timestamp formattato
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")
