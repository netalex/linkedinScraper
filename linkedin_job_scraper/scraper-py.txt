"""
Funzionalità di scraping principale per LinkedIn Job Scraper.
Gestisce l'estrazione dei dati dalle pagine delle offerte di lavoro e la loro elaborazione.
"""

import datetime
import re
import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup

from .utils import extract_job_id_from_url, make_request_with_backoff, get_request_headers
from .api import try_api_endpoint, extract_job_ids_from_search
from .models import validate_job_data, create_empty_job_data, enrich_job_data_for_application


def extract_data_from_html(html_content: str, job_url: str) -> Dict[str, Any]:
    """
    Estrae i dati dell'offerta dal contenuto HTML di una pagina di offerta di lavoro LinkedIn.
    
    Args:
        html_content: Contenuto HTML della pagina dell'offerta
        job_url: URL dell'offerta
        
    Returns:
        Dizionario contenente i dati estratti dell'offerta
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Inizializza con i campi richiesti
    job_data = create_empty_job_data()
    job_data["Detail URL"] = job_url
    job_data["ScrapedAt"] = datetime.datetime.now().isoformat()
    
    # Estrai il titolo dell'offerta
    title_element = soup.select_one('h1.top-card-layout__title')
    if title_element:
        job_data["Title"] = title_element.get_text().strip()
    
    # Estrai la descrizione dell'offerta
    description_element = soup.select_one('div.description__text')
    if description_element:
        job_data["Description"] = description_element.get_text().strip()
    
    # Estrai la posizione
    location_element = soup.select_one('span.topcard__flavor--bullet')
    if location_element:
        job_data["Location"] = location_element.get_text().strip()
    
    # Estrai il nome dell'azienda
    company_name_element = soup.select_one('a.topcard__org-name-link')
    if company_name_element:
        job_data["Company Name"] = company_name_element.get_text().strip()
    
    # Estrai il logo dell'azienda
    company_logo_element = soup.select_one('img.artdeco-entity-image')
    if company_logo_element and 'src' in company_logo_element.attrs:
        job_data["Company Logo"] = company_logo_element['src']
    
    # Estrai l'URL per la candidatura
    apply_button = soup.select_one('a.apply-button')
    if apply_button and 'href' in apply_button.attrs:
        job_data["Company Apply Url"] = apply_button['href']
    else:
        job_data["Company Apply Url"] = f"https://www.linkedin.com/job-apply/{job_url.split('/')[-1].split('?')[0]}"
    
    # Estrai la descrizione dell'azienda e altri dettagli dalla sezione "about"
    company_about = soup.select_one('div.company-description')
    if company_about:
        job_data["Company Description"] = company_about.get_text().strip()
    
    # Il sito web dell'azienda potrebbe essere nella sezione "about" o altrove
    company_website_element = soup.select_one('a[href*="://"].link-without-visited-state')
    if company_website_element:
        job_data["Company Website"] = company_website_element['href']
    
    # Estrai altri metadati dell'azienda
    company_details = soup.select('dd.top-card-layout__card-elements')
    for detail in company_details:
        text = detail.get_text().strip()
        if "employees" in text.lower():
            # Estrai il numero di dipendenti
            numbers = re.findall(r'\d+', text.replace(',', ''))
            if numbers:
                try:
                    if len(numbers) >= 2:
                        job_data["Employee Count"] = (int(numbers[0]) + int(numbers[1])) // 2
                    else:
                        job_data["Employee Count"] = int(numbers[0])
                except (ValueError, TypeError):
                    pass
        elif "headquarters" in text.lower():
            job_data["Headquarters"] = text.replace("Headquarters:", "").strip()
        elif "industry" in text.lower():
            job_data["Industry"] = text.replace("Industry:", "").strip()
        elif "founded" in text.lower():
            year_match = re.search(r'\b\d{4}\b', text)
            if year_match:
                try:
                    job_data["Company Founded"] = int(year_match.group(0))
                except ValueError:
                    pass
    
    # Estrai specializzazioni se disponibili
    specialties_element = soup.select_one('div.specialties')
    if specialties_element:
        job_data["Specialties"] = specialties_element.get_text().strip()
    
    # Estrai Poster ID se disponibile
    poster_element = soup.select_one('[data-poster-id]')
    if poster_element and 'data-poster-id' in poster_element.attrs:
        job_data["Poster Id"] = poster_element['data-poster-id']
    else:
        # Fallback su ID azienda se disponibile
        company_id_element = soup.select_one('[data-company-id]')
        if company_id_element and 'data-company-id' in company_id_element.attrs:
            job_data["Poster Id"] = company_id_element['data-company-id']
        else:
            # Genera un ID fallback basato sul nome dell'azienda
            if job_data["Company Name"]:
                job_data["Poster Id"] = str(hash(job_data["Company Name"]) % 10000000)
    
    # Estrai data di pubblicazione
    posted_date_element = soup.select_one('span.posted-date')
    if posted_date_element:
        posted_text = posted_date_element.get_text().strip()
        # Gestisci diversi formati di data
        days_ago_match = re.search(r'(\d+)\s+days?\s+ago', posted_text)
        if days_ago_match:
            days_ago = int(days_ago_match.group(1))
            created_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            job_data["Created At"] = created_date.isoformat()
        elif "week" in posted_text.lower():
            weeks_match = re.search(r'(\d+)\s+weeks?\s+ago', posted_text)
            if weeks_match:
                weeks_ago = int(weeks_match.group(1))
                created_date = datetime.datetime.now() - datetime.timedelta(weeks=weeks_ago)
                job_data["Created At"] = created_date.isoformat()
        elif "month" in posted_text.lower():
            months_match = re.search(r'(\d+)\s+months?\s+ago', posted_text)
            if months_match:
                months_ago = int(months_match.group(1))
                created_date = datetime.datetime.now() - datetime.timedelta(days=30*months_ago)
                job_data["Created At"] = created_date.isoformat()
        elif "today" in posted_text.lower():
            job_data["Created At"] = datetime.datetime.now().isoformat()
        elif "yesterday" in posted_text.lower():
            created_date = datetime.datetime.now() - datetime.timedelta(days=1)
            job_data["Created At"] = created_date.isoformat()
    
    return job_data


def extract_data_from_api_response(api_response: Dict[str, Any], job_url: str) -> Dict[str, Any]:
    """
    Estrae i dati dell'offerta dalla risposta API di LinkedIn.
    
    Args:
        api_response: Dati della risposta API
        job_url: URL dell'offerta
        
    Returns:
        Dizionario contenente i dati estratti dell'offerta
    """
    # Controlla se abbiamo ricevuto HTML invece di JSON
    if "html_content" in api_response:
        return extract_data_from_html(api_response["html_content"], job_url)
    
    # Inizializza con i campi richiesti
    job_data = create_empty_job_data()
    job_data["Detail URL"] = job_url
    job_data["ScrapedAt"] = datetime.datetime.now().isoformat()
    
    # Controlla se abbiamo il formato JSON-LD
    if "@type" in api_response and api_response.get("@type") == "JobPosting":
        # Elabora il formato JSON-LD
        job_data["Title"] = api_response.get("title")
        job_data["Description"] = api_response.get("description")
        
        # Posizione
        if "jobLocation" in api_response:
            address = api_response["jobLocation"].get("address", {})
            location_parts = []
            
            if "addressLocality" in address:
                location_parts.append(address["addressLocality"])
            if "addressRegion" in address:
                location_parts.append(address["addressRegion"])
            if "addressCountry" in address:
                country = address["addressCountry"]
                if isinstance(country, dict) and "name" in country:
                    location_parts.append(country["name"])
                elif isinstance(country, str):
                    location_parts.append(country)
            
            job_data["Location"] = ", ".join(location_parts)
        
        # Dettagli dell'azienda
        if "hiringOrganization" in api_response:
            org = api_response["hiringOrganization"]
            job_data["Company Name"] = org.get("name")
            job_data["Company Logo"] = org.get("logo", {}).get("url") if isinstance(org.get("logo"), dict) else org.get("logo")
            job_data["Company Website"] = org.get("sameAs")
            job_data["Poster Id"] = str(hash(org.get("name", "")) % 10000000) if org.get("name") else None
        
        # Data
        if "datePosted" in api_response:
            try:
                posted_date = datetime.datetime.fromisoformat(api_response["datePosted"].replace('Z', '+00:00'))
                job_data["Created At"] = posted_date.isoformat()
            except (ValueError, AttributeError):
                pass
        
        # URL candidatura
        job_data["Company Apply Url"] = api_response.get("url", job_url)
        
        return job_data
    
    # Formato di risposta API standard
    if 'title' in api_response:
        job_data["Title"] = api_response['title']
    
    if 'description' in api_response:
        # Pulisci l'HTML dalla descrizione
        description_html = api_response['description']
        if isinstance(description_html, str):
            description_text = re.sub(r'<[^>]+>', ' ', description_html)
            description_text = re.sub(r'\s+', ' ', description_text).strip()
            job_data["Description"] = description_text
    
    if 'formattedLocation' in api_response:
        job_data["Location"] = api_response['formattedLocation']
    elif 'location' in api_response:
        job_data["Location"] = api_response['location']
    
    # Dettagli dell'azienda
    company = api_response.get('companyDetails', {})
    if not company and 'company' in api_response:
        company = api_response['company']
    
    if company:
        if 'name' in company:
            job_data["Company Name"] = company['name']
        elif 'companyName' in company:
            job_data["Company Name"] = company['companyName']
        
        if 'logoUrl' in company:
            job_data["Company Logo"] = company['logoUrl']
        elif 'logo' in company:
            job_data["Company Logo"] = company['logo']
        
        if 'companyId' in company:
            job_data["Poster Id"] = str(company['companyId'])
        elif 'id' in company:
            job_data["Poster Id"] = str(company['id'])
        
        if 'description' in company:
            job_data["Company Description"] = company['description']
        
        if 'websiteUrl' in company:
            job_data["Company Website"] = company['websiteUrl']
        elif 'website' in company:
            job_data["Company Website"] = company['website']
        
        if 'industry' in company:
            job_data["Industry"] = company['industry']
        
        if 'employeeCount' in company:
            try:
                count = company['employeeCount']
                if isinstance(count, str):
                    # Estrai numeri da testo come "1,000-5,000 employees"
                    numbers = re.findall(r'\d+', count.replace(',', ''))
                    if numbers:
                        if len(numbers) >= 2:
                            job_data["Employee Count"] = (int(numbers[0]) + int(numbers[1])) // 2
                        else:
                            job_data["Employee Count"] = int(numbers[0])
                elif isinstance(count, (int, float)):
                    job_data["Employee Count"] = int(count)
            except (ValueError, TypeError):
                pass
        
        if 'headquarters' in company:
            job_data["Headquarters"] = company['headquarters']
        
        if 'foundedYear' in company:
            try:
                job_data["Company Founded"] = int(company['foundedYear'])
            except (ValueError, TypeError):
                pass
        
        if 'specialties' in company:
            specialties = company['specialties']
            if isinstance(specialties, list):
                job_data["Specialties"] = ", ".join(specialties)
            else:
                job_data["Specialties"] = str(specialties)
    
    if 'applyUrl' in api_response:
        job_data["Company Apply Url"] = api_response['applyUrl']
    elif 'applicationUrl' in api_response:
        job_data["Company Apply Url"] = api_response['applicationUrl']
    
    if 'listedAt' in api_response:
        try:
            listed_timestamp = float(api_response['listedAt']) / 1000  # Converti millisecondi in secondi
            listed_date = datetime.datetime.fromtimestamp(listed_timestamp)
            job_data["Created At"] = listed_date.isoformat()
        except (ValueError, TypeError, OverflowError):
            pass
    elif 'postingDate' in api_response:
        try:
            job_data["Created At"] = api_response['postingDate']
        except (ValueError, TypeError):
            pass
    
    return job_data


def clean_and_validate_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pulisce e convalida i dati dell'offerta per garantire che siano conformi allo schema.
    
    Args:
        job_data: Dati grezzi dell'offerta
        
    Returns:
        Dati dell'offerta puliti e convalidati
    """
    cleaned_data = job_data.copy()
    
    # Assicurati che Employee Count sia un intero o null
    if cleaned_data["Employee Count"] is not None:
        try:
            cleaned_data["Employee Count"] = int(cleaned_data["Employee Count"])
        except (ValueError, TypeError):
            cleaned_data["Employee Count"] = None
    
    # Assicurati che Company Founded sia un intero o null
    if cleaned_data["Company Founded"] is not None:
        try:
            cleaned_data["Company Founded"] = int(cleaned_data["Company Founded"])
        except (ValueError, TypeError):
            cleaned_data["Company Founded"] = None
    
    # Assicurati che tutti i campi stringa siano stringhe e non vuoti
    for key, value in cleaned_data.items():
        if value == "":
            cleaned_data[key] = None
        elif value is not None and not isinstance(value, (str, int)):
            cleaned_data[key] = str(value)
    
    # Imposta valori predefiniti per i campi richiesti che potrebbero mancare
    if cleaned_data["Title"] is None:
        cleaned_data["Title"] = "Untitled Job"
    
    if cleaned_data["Description"] is None:
        cleaned_data["Description"] = "No description provided"
    
    if cleaned_data["Location"] is None:
        cleaned_data["Location"] = "Remote"
    
    if cleaned_data["Company Name"] is None:
        cleaned_data["Company Name"] = "Unknown Company"
    
    if cleaned_data["Industry"] is None:
        cleaned_data["Industry"] = "Information Technology"
    
    if cleaned_data["Headquarters"] is None:
        cleaned_data["Headquarters"] = "Unknown"
    
    if cleaned_data["Specialties"] is None:
        cleaned_data["Specialties"] = "Not specified"
    
    if cleaned_data["Poster Id"] is None:
        cleaned_data["Poster Id"] = "000000"
    
    if cleaned_data["Company Logo"] is None:
        cleaned_data["Company Logo"] = "https://static.licdn.com/aero-v1/sc/h/dbvmk0tsk0o0hd59fi64z3own"
    
    if cleaned_data["Company Apply Url"] is None:
        cleaned_data["Company Apply Url"] = cleaned_data["Detail URL"]
    
    if cleaned_data["Company Website"] is None:
        cleaned_data["Company Website"] = "https://www.linkedin.com/"
    
    if cleaned_data["Company Description"] is None:
        cleaned_data["Company Description"] = "No company description provided"
    
    # Assicurati che Created At sia una stringa di data ISO valida
    if cleaned_data["Created At"] is None:
        # Se non abbiamo una data di creazione, usa 30 giorni fa come predefinito
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        cleaned_data["Created At"] = thirty_days_ago.isoformat()
    
    return cleaned_data


def scrape_linkedin_job(job_url: str, min_delay: int = 1, max_delay: int = 3,
                       proxy_url: str = None, enrich: bool = False) -> Optional[Dict[str, Any]]:
    """
    Scrape un'offerta di lavoro LinkedIn e restituisci i dati nel formato richiesto.
    
    Args:
        job_url: URL dell'offerta di lavoro LinkedIn
        min_delay: Ritardo minimo tra le richieste
        max_delay: Ritardo massimo tra le richieste
        proxy_url: URL del proxy opzionale
        enrich: Arricchisci i dati con campi per il tracciamento delle candidature
        
    Returns:
        Dizionario contenente i dati dell'offerta se con successo, None altrimenti
    """
    job_id = extract_job_id_from_url(job_url)
    if not job_id:
        logging.error(f"Impossibile estrarre l'ID dell'offerta dall'URL: {job_url}")
        return None
    
    logging.info(f"ID offerta estratto: {job_id}")
    
    # Prima, prova a utilizzare l'endpoint API
    api_response = try_api_endpoint(job_id, min_delay, max_delay, proxy_url)
    if api_response:
        logging.info("Dati ottenuti con successo dall'endpoint API")
        job_data = extract_data_from_api_response(api_response, job_url)
    else:
        logging.info("Impossibile ottenere dati dall'endpoint API, fallback allo scraping HTML")
        # Fallback allo scraping della pagina HTML
        html_content = make_request_with_backoff(job_url, min_delay=min_delay, max_delay=max_delay, proxy_url=proxy_url)
        if not html_content:
            logging.error("Impossibile recuperare il contenuto HTML")
            return None
        
        job_data = extract_data_from_html(html_content, job_url)
    
    # Pulisci e convalida i dati
    cleaned_data = clean_and_validate_job_data(job_data)
    
    # Arricchisci i dati se richiesto
    if enrich:
        cleaned_data = enrich_job_data_for_application(cleaned_data)
    
    return cleaned_data


def process_search_results(search_url: str, output_file: str, max_jobs: int = 100,
                         min_delay: int = 2, max_delay: int = 5, proxy_url: str = None,
                         enrich: bool = False) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Elabora i risultati della ricerca di lavoro e salva i dati in un file JSON.
    
    Args:
        search_url: URL di ricerca di lavoro LinkedIn
        output_file: Percorso del file JSON di output
        max_jobs: Numero massimo di offerte da elaborare
        min_delay: Ritardo minimo tra le richieste
        max_delay: Ritardo massimo tra le richieste
        proxy_url: URL del proxy opzionale
        enrich: Arricchisci i dati con campi per il tracciamento delle candidature
        
    Returns:
        Tupla (successo, dati di tutte le offerte)
    """
    logging.info(f"Elaborazione dei risultati di ricerca da: {search_url}")
    
    # Estrai gli ID delle offerte dai risultati di ricerca
    job_ids = extract_job_ids_from_search(
        search_url, 
        max_jobs=max_jobs,
        min_delay=min_delay,
        max_delay=max_delay,
        proxy_url=proxy_url
    )
    
    if not job_ids:
        logging.error("Nessun ID offerta trovato nei risultati di ricerca")
        return False, []
    
    logging.info(f"Trovati {len(job_ids)} ID offerta")
    
    # Elabora ogni ID offerta
    all_jobs_data = []
    for i, job_id in enumerate(job_ids):
        logging.info(f"Elaborazione offerta {i+1}/{len(job_ids)}: {job_id}")
        
        # Costruisci l'URL dell'offerta
        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        
        # Scrape dei dati dell'offerta
        job_data = scrape_linkedin_job(
            job_url,
            min_delay=min_delay,
            max_delay=max_delay,
            proxy_url=proxy_url,
            enrich=enrich
        )
        
        if not job_data:
            logging.warning(f"Impossibile effettuare lo scraping dell'offerta {job_id}")
            continue
        
        # Convalida i dati dell'offerta
        if not validate_job_data(job_data):
            logging.warning(f"I dati dell'offerta {job_id} non hanno superato la convalida")
            continue
        
        # Aggiungi ai dati di tutte le offerte
        all_jobs_data.append(job_data)
        
        # Aggiungi un ritardo tra le richieste di offerte
        time.sleep(random.uniform(min_delay, max_delay))
    
    if not all_jobs_data:
        logging.error("Nessun dato offerta valido trovato")
        return False, []
    
    # Salva tutti i dati delle offerte in un file JSON
    from exporters.json_exporter import save_jobs_data_to_json
    success = save_jobs_data_to_json(all_jobs_data, output_file)
    
    return success, all_jobs_data
