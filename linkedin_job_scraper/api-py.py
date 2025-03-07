"""
Funzioni per interagire con le API di LinkedIn.
Gestisce le richieste agli endpoint di LinkedIn e l'estrazione dei dati dalle risposte.
"""

import re
import json
import time
import random
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from .utils import get_request_headers, make_request_with_backoff, extract_job_id_from_url


def extract_job_ids_from_search(search_url: str, max_jobs: int = 100,
                              min_delay: int = 2, max_delay: int = 5,
                              proxy_url: str = None) -> List[str]:
    """
    Estrae gli ID delle offerte di lavoro da una pagina di risultati di ricerca di LinkedIn.
    
    Args:
        search_url: URL di ricerca di lavoro di LinkedIn
        max_jobs: Numero massimo di offerte da estrarre
        min_delay: Ritardo minimo tra le richieste
        max_delay: Ritardo massimo tra le richieste
        proxy_url: URL del proxy opzionale
        
    Returns:
        Lista di ID di offerte
    """
    job_ids = []
    page_num = 0
    jobs_found = 0
    
    logging.info(f"Estrazione degli ID delle offerte dalla ricerca: {search_url}")
    
    # Determina se stiamo utilizzando l'API guest o la ricerca standard
    is_guest_api = "jobs-guest/jobs/api" in search_url
    
    while jobs_found < max_jobs:
        # Regola il parametro di paginazione in base al tipo di URL
        if is_guest_api:
            # L'API guest utilizza il parametro pageNum
            if "pageNum=" in search_url:
                current_page_url = re.sub(r'pageNum=\d+', f'pageNum={page_num}', search_url)
            else:
                separator = "&" if "?" in search_url else "?"
                current_page_url = f"{search_url}{separator}pageNum={page_num}"
        else:
            # La ricerca regolare utilizza il parametro start (25 offerte per pagina)
            start_value = page_num * 25
            if "start=" in search_url:
                current_page_url = re.sub(r'start=\d+', f'start={start_value}', search_url)
            else:
                separator = "&" if "?" in search_url else "?"
                current_page_url = f"{search_url}{separator}start={start_value}"
        
        # Effettua la richiesta con backoff e rotazione degli user agent
        headers = get_request_headers()
        response_text = make_request_with_backoff(
            current_page_url, 
            headers,
            min_delay=min_delay,
            max_delay=max_delay,
            proxy_url=proxy_url
        )
        
        if not response_text:
            logging.error(f"Impossibile ottenere la pagina dei risultati {page_num}")
            break
        
        # Analizza l'HTML con BeautifulSoup
        soup = BeautifulSoup(response_text, 'html.parser')
        
        # Estrai gli ID delle offerte in base al tipo di URL
        if is_guest_api:
            # L'API guest restituisce elementi li con ID delle offerte
            job_items = soup.select('li')
            if not job_items:
                # Prova selettore alternativo per le schede delle offerte
                job_items = soup.select('div.job-search-card')
                
            if not job_items:
                logging.info(f"Nessun altro elemento offerta trovato nella pagina {page_num}")
                break
                
            for item in job_items:
                # Tenta di estrarre l'ID dell'offerta da vari attributi
                job_id = None
                
                # Controlla l'attributo data-id
                if 'data-id' in item.attrs:
                    job_id = item['data-id']
                # Controlla l'attributo data-job-id
                elif 'data-job-id' in item.attrs:
                    job_id = item['data-job-id']
                # Controlla il link dell'offerta
                else:
                    job_link = item.select_one('a[href*="/jobs/view/"]')
                    if job_link and 'href' in job_link.attrs:
                        job_id = extract_job_id_from_url(job_link['href'])
                
                if job_id and job_id not in job_ids:
                    job_ids.append(job_id)
                    jobs_found += 1
                    
                    if jobs_found >= max_jobs:
                        break
        else:
            # Ricerca regolare - estrai gli ID dalle schede delle offerte
            job_cards = soup.select('div.job-card-container')
            if not job_cards:
                job_cards = soup.select('div.base-card')
            
            if not job_cards:
                logging.info(f"Nessun'altra scheda offerta trovata nella pagina {page_num}")
                break
                
            for card in job_cards:
                # Estrai l'ID dell'offerta dalla scheda
                job_id = None
                
                # Controlla l'attributo data-job-id
                if 'data-job-id' in card.attrs:
                    job_id = card['data-job-id']
                else:
                    # Cerca il link dell'offerta
                    job_link = card.select_one('a[href*="/jobs/view/"]')
                    if job_link and 'href' in job_link.attrs:
                        job_id = extract_job_id_from_url(job_link['href'])
                
                if job_id and job_id not in job_ids:
                    job_ids.append(job_id)
                    jobs_found += 1
                    
                    if jobs_found >= max_jobs:
                        break
        
        # Controlla se abbiamo trovato offerte in questa pagina
        new_jobs_on_page = len(job_ids) - (jobs_found - len(job_ids))
        if new_jobs_on_page == 0:
            logging.info(f"Nessuna nuova offerta trovata nella pagina {page_num}")
            break
            
        logging.info(f"Trovati {len(job_ids)} ID offerta finora (pagina {page_num})")
        page_num += 1
        
        # Ritardo casuale prima della prossima richiesta di pagina (più variazione)
        time.sleep(random.uniform(min_delay, max_delay))
    
    return job_ids


def try_api_endpoint(job_id: str, min_delay: int = 1, max_delay: int = 3,
                   proxy_url: str = None) -> Optional[Dict[str, Any]]:
    """
    Tenta di ottenere i dettagli dell'offerta dall'endpoint API di LinkedIn.
    
    Args:
        job_id: ID dell'offerta di LinkedIn
        min_delay: Ritardo minimo prima della richiesta
        max_delay: Ritardo massimo prima della richiesta
        proxy_url: URL del proxy opzionale
        
    Returns:
        Dati della risposta API se con successo, None altrimenti
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = get_request_headers()
    
    # Regola gli header per la richiesta API
    headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
    headers['X-Requested-With'] = 'XMLHttpRequest'
    
    # Ritardo casuale prima della richiesta
    time.sleep(random.uniform(min_delay, max_delay))
    
    response_text = make_request_with_backoff(url, headers, proxy_url=proxy_url)
    if not response_text:
        return None
    
    try:
        # LinkedIn potrebbe restituire HTML anche per l'endpoint API, quindi controlla i marker JSON
        if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            return json.loads(response_text)
        else:
            # Elabora la risposta HTML ed estrai i dati strutturati
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Controlla lo script JSON-LD (dati strutturati)
            json_ld = soup.select_one('script[type="application/ld+json"]')
            if json_ld:
                try:
                    return json.loads(json_ld.string)
                except json.JSONDecodeError:
                    pass
            
            # Restituisci il contenuto HTML per l'elaborazione fallback
            return {"html_content": response_text}
    except json.JSONDecodeError:
        logging.error(f"Impossibile analizzare la risposta JSON dall'endpoint API")
        return {"html_content": response_text}
