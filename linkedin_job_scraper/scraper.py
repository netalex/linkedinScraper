"""
Funzionalità di scraping principale per LinkedIn Job Scraper.
Gestisce l'estrazione dei dati dalle pagine delle offerte di lavoro e la loro elaborazione.
"""

import datetime
import re
import time
import random
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union

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
    
    # Estrai il titolo dell'offerta (utilizzo di selettori multipli per maggiore robustezza)
    title_selectors = [
        'h1.top-card-layout__title',
        'h1.job-details-jobs-unified-top-card__job-title',
        'h1.topcard__title',
        'h1.jobs-unified-top-card__job-title'
    ]
    
    for selector in title_selectors:
        title_element = soup.select_one(selector)
        if title_element:
            job_data["Title"] = title_element.get_text().strip()
            break
    
    # Estrai la descrizione dell'offerta (selettori multipli)
    description_selectors = [
        'div.description__text',
        'div.show-more-less-html__markup',
        'div.jobs-description-content__text',
        'div.job-details-jobs-unified-description__container'
    ]
    
    for selector in description_selectors:
        description_element = soup.select_one(selector)
        if description_element:
            job_data["Description"] = description_element.get_text().strip()
            break
    
    # Estrai la posizione (selettori multipli)
    location_selectors = [
        'span.topcard__flavor--bullet',
        'span.job-details-jobs-unified-top-card__bullet',
        'span.jobs-unified-top-card__bullet',
        'span.jobs-unified-top-card__workplace-type'
    ]
    
    for selector in location_selectors:
        location_element = soup.select_one(selector)
        if location_element:
            job_data["Location"] = location_element.get_text().strip()
            break
    
    # Controlla anche nel testo della posizione per "Remote" o simili
    if job_data["Location"] and ("remote" in job_data["Location"].lower() or "remoto" in job_data["Location"].lower()):
        if not "Remote" in job_data["Location"]:
            job_data["Location"] = f"{job_data['Location']} (Remote)"
    
    # Estrai il nome dell'azienda (selettori multipli)
    company_name_selectors = [
        'a.topcard__org-name-link',
        'a.job-details-jobs-unified-top-card__company-name',
        'a.jobs-unified-top-card__company-name',
        'span.topcard__org-name-link',
        'span.job-details-jobs-unified-top-card__company-name'
    ]
    
    for selector in company_name_selectors:
        company_name_element = soup.select_one(selector)
        if company_name_element:
            job_data["Company Name"] = company_name_element.get_text().strip()
            break
    
    # Estrai il logo dell'azienda (selettori multipli)
    logo_selectors = [
        'img.artdeco-entity-image',
        'img.job-details-jobs-unified-top-card__company-logo',
        'img.jobs-unified-top-card__company-logo',
        'img.topcard__org-logo-img'
    ]
    
    for selector in logo_selectors:
        logo_element = soup.select_one(selector)
        if logo_element and 'src' in logo_element.attrs:
            job_data["Company Logo"] = logo_element['src']
            break
    
    # Estrai l'URL per la candidatura
    apply_button_selectors = [
        'a.apply-button',
        'a.jobs-apply-button',
        'a[data-tracking-control-name="public_jobs_apply-link-offsite_sign-up"]',
        'a.job-details-jobs-unified-top-card__apply-button'
    ]
    
    for selector in apply_button_selectors:
        apply_button = soup.select_one(selector)
        if apply_button and 'href' in apply_button.attrs:
            job_data["Company Apply Url"] = apply_button['href']
            break
    
    # Se non troviamo un URL di candidatura, costruisci l'URL standard di LinkedIn
    if not job_data["Company Apply Url"]:
        job_id = extract_job_id_from_url(job_url)
        if job_id:
            job_data["Company Apply Url"] = f"https://www.linkedin.com/job-apply/{job_id}/"
        else:
            job_data["Company Apply Url"] = job_url
    
    # Estrai la descrizione dell'azienda
    company_description_selectors = [
        'div.company-description',
        'div.jobs-company__box',
        'p.job-details-jobs-unified-top-card__company-description',
        'div.jobs-company-details'
    ]
    
    for selector in company_description_selectors:
        company_about = soup.select_one(selector)
        if company_about:
            job_data["Company Description"] = company_about.get_text().strip()
            break
    
    # Estrai il sito web dell'azienda
    website_selectors = [
        'a[href*="://"].link-without-visited-state',
        'a.jobs-company__link',
        'a[data-tracking-control-name="public_jobs_topcard-company-url"]'
    ]
    
    for selector in website_selectors:
        company_website_element = soup.select_one(selector)
        if company_website_element and 'href' in company_website_element.attrs:
            url = company_website_element['href']
            # Verifica che sia un URL valido e non un percorso interno LinkedIn
            if url.startswith('http') and 'linkedin.com' not in url:
                job_data["Company Website"] = url
                break
    
    # Estrai dettagli dell'azienda
    company_details_selectors = [
        'dd.top-card-layout__card-elements',
        'dd.jobs-company__card-elements',
        'span.jobs-company__secondary-information',
        'div.job-details-jobs-unified-top-card__primary-description'
    ]
    
    all_details = []
    for selector in company_details_selectors:
        all_details.extend(soup.select(selector))
    
    if all_details:
        for detail in all_details:
            text = detail.get_text().strip()
            # Estrai numero di dipendenti
            if "employees" in text.lower() or "dipendenti" in text.lower():
                numbers = re.findall(r'\d+[\s,\.]*\d*', text.replace(',', ''))
                if numbers:
                    try:
                        # Se è un range (es. "1,000-5,000"), calcola la media
                        if len(numbers) >= 2:
                            num1 = int(re.sub(r'[^\d]', '', numbers[0]))
                            num2 = int(re.sub(r'[^\d]', '', numbers[1]))
                            job_data["Employee Count"] = (num1 + num2) // 2
                        else:
                            job_data["Employee Count"] = int(re.sub(r'[^\d]', '', numbers[0]))
                    except (ValueError, TypeError):
                        pass
            
            # Estrai sede centrale
            if "headquarters" in text.lower() or "sede" in text.lower():
                headquarters = re.sub(r'headquarters:?\s*|sede:?\s*', '', text, flags=re.IGNORECASE).strip()
                if headquarters:
                    job_data["Headquarters"] = headquarters
            
            # Estrai settore
            if "industry" in text.lower() or "settore" in text.lower():
                industry = re.sub(r'industry:?\s*|settore:?\s*', '', text, flags=re.IGNORECASE).strip()
                if industry:
                    job_data["Industry"] = industry
            
            # Estrai anno di fondazione
            if "founded" in text.lower() or "fondata" in text.lower():
                year_match = re.search(r'\b(19|20)\d{2}\b', text)
                if year_match:
                    try:
                        job_data["Company Founded"] = int(year_match.group(0))
                    except ValueError:
                        pass
    
    # Estrai specializzazioni (selettori multipli)
    specialties_selectors = [
        'div.specialties',
        'ul.jobs-company__specialties',
        'ul.job-details-jobs-unified-top-card__specialties'
    ]
    
    for selector in specialties_selectors:
        specialties_element = soup.select_one(selector)
        if specialties_element:
            spec_text = specialties_element.get_text().strip()
            # Pulisci il testo da eventuali prefissi
            spec_text = re.sub(r'specialties:?\s*|specializzazioni:?\s*', '', spec_text, flags=re.IGNORECASE)
            job_data["Specialties"] = spec_text
            break
    
    # Estrai Poster ID (con vari metodi)
    poster_selectors = [
        '[data-poster-id]',
        '[data-job-poster-id]',
        '[data-company-id]',
        '[data-entity-urn]'
    ]
    
    for selector in poster_selectors:
        poster_element = soup.select_one(selector)
        if poster_element:
            for attr in ['data-poster-id', 'data-job-poster-id', 'data-company-id']:
                if attr in poster_element.attrs:
                    job_data["Poster Id"] = poster_element[attr]
                    break
            
            # Se non è stato trovato in attributi diretti, cerca in data-entity-urn
            if not job_data["Poster Id"] and 'data-entity-urn' in poster_element.attrs:
                urn_match = re.search(r':(\d+)$', poster_element['data-entity-urn'])
                if urn_match:
                    job_data["Poster Id"] = urn_match.group(1)
    
    # Se ancora non è stato trovato, genera un ID basato sul nome dell'azienda
    if not job_data["Poster Id"] and job_data["Company Name"]:
        job_data["Poster Id"] = str(abs(hash(job_data["Company Name"])) % 10000000)
    
    # Estrai la data di pubblicazione (selettori multipli)
    date_selectors = [
        'span.posted-date',
        'span.topcard__flavor--metadata',
        'span.job-details-jobs-unified-top-card__posted-date',
        'time.job-details-jobs-unified-top-card__posted-date',
        'span.jobs-unified-top-card__posted-date'
    ]
    
    for selector in date_selectors:
        date_element = soup.select_one(selector)
        if date_element:
            posted_text = date_element.get_text().strip()
            created_at = parse_posted_date(posted_text)
            if created_at:
                job_data["Created At"] = created_at
                break
    
    # Verifica se la pagina contiene informazioni del hiring manager
    hiring_manager_selectors = [
        '.hiring-manager',
        '.jobs-poster',
        '.job-details-jobs-unified-top-card__hiring-manager'
    ]
    
    for selector in hiring_manager_selectors:
        hiring_manager = soup.select_one(selector)
        if hiring_manager:
            # Informazioni del manager sono presenti, ma le impostiamo a null come da schema
            job_data["Hiring Manager Title"] = None
            job_data["Hiring Manager Subtitle"] = None
            job_data["Hiring Manager Title Insight"] = None
            job_data["Hiring Manager Profile"] = None
            job_data["Hiring Manager Image"] = None
            break
    
    return job_data


def parse_posted_date(posted_text: str) -> Optional[str]:
    """
    Analizza il testo della data di pubblicazione e lo converte in formato ISO.
    
    Args:
        posted_text: Testo della data di pubblicazione (es. "3 days ago", "Posted 2 weeks ago")
        
    Returns:
        Data in formato ISO o None se non può essere analizzata
    """
    now = datetime.datetime.now()
    
    # Rimuovi prefissi comuni
    clean_text = re.sub(r'^posted\s+|pubblicato\s+', '', posted_text, flags=re.IGNORECASE).strip()
    
    # Pattern per "X days ago"
    days_ago_match = re.search(r'(\d+)\s+day[s]?\s+ago', clean_text, re.IGNORECASE)
    if days_ago_match:
        days_ago = int(days_ago_match.group(1))
        created_date = now - datetime.timedelta(days=days_ago)
        return created_date.isoformat()
    
    # Pattern per "X weeks ago"
    weeks_match = re.search(r'(\d+)\s+week[s]?\s+ago', clean_text, re.IGNORECASE)
    if weeks_match:
        weeks_ago = int(weeks_match.group(1))
        created_date = now - datetime.timedelta(weeks=weeks_ago)
        return created_date.isoformat()
    
    # Pattern per "X months ago"
    months_match = re.search(r'(\d+)\s+month[s]?\s+ago', clean_text, re.IGNORECASE)
    if months_match:
        months_ago = int(months_match.group(1))
        created_date = now - datetime.timedelta(days=30*months_ago)
        return created_date.isoformat()
    
    # Parole chiave
    if re.search(r'\btoday\b|\boggi\b', clean_text, re.IGNORECASE):
        return now.isoformat()
    
    if re.search(r'\byesterday\b|\bieri\b', clean_text, re.IGNORECASE):
        created_date = now - datetime.timedelta(days=1)
        return created_date.isoformat()
    
    if re.search(r'\bjust now\b|\bappena\b', clean_text, re.IGNORECASE):
        return now.isoformat()
    
    # Data specifica (formato: "Mar 15, 2023")
    date_match = re.search(r'([a-z]{3})\s+(\d{1,2}),?\s+(\d{4})', clean_text, re.IGNORECASE)
    if date_match:
        try:
            month_str, day_str, year_str = date_match.groups()
            month_mapping = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                'gen': 1, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'dic': 12
            }
            month = month_mapping.get(month_str.lower(), 1)
            day = int(day_str)
            year = int(year_str)
            created_date = datetime.datetime(year, month, day)
            return created_date.isoformat()
        except (ValueError, KeyError):
            pass
    
    # Fallback: 30 giorni fa
    return (now - datetime.timedelta(days=30)).isoformat()


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
        
        # Rimuovi tag HTML dalla descrizione
        if job_data["Description"] and '<' in job_data["Description"]:
            job_data["Description"] = BeautifulSoup(job_data["Description"], 'html.parser').get_text()
        
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
            
            # Verifica se è remoto
            if "remote" in str(api_response).lower():
                if job_data["Location"] and "remote" not in job_data["Location"].lower():
                    job_data["Location"] += " (Remote)"
        
        # Dettagli dell'azienda
        if "hiringOrganization" in api_response:
            org = api_response["hiringOrganization"]
            job_data["Company Name"] = org.get("name")
            
            # Logo
            if "logo" in org:
                logo = org["logo"]
                if isinstance(logo, dict) and "url" in logo:
                    job_data["Company Logo"] = logo["url"]
                elif isinstance(logo, str):
                    job_data["Company Logo"] = logo
            
            # Sito web dell'azienda
            if "sameAs" in org:
                job_data["Company Website"] = org["sameAs"]
            
            # Poster ID
            if "identifier" in org:
                identifier = org["identifier"]
                if isinstance(identifier, str):
                    job_data["Poster Id"] = identifier
                elif isinstance(identifier, dict) and "value" in identifier:
                    job_data["Poster Id"] = str(identifier["value"])
                else:
                    job_data["Poster Id"] = str(hash(org.get("name", "")) % 10000000)
            else:
                job_data["Poster Id"] = str(hash(org.get("name", "")) % 10000000)
            
            # Descrizione azienda
            if "description" in org:
                job_data["Company Description"] = org["description"]
        
        # Data
        if "datePosted" in api_response:
            try:
                # Gestisci diversi formati di data ISO
                date_string = api_response["datePosted"]
                if 'Z' in date_string:
                    date_string = date_string.replace('Z', '+00:00')
                
                # Per compatibilità con versioni Python precedenti alla 3.7
                if '+' in date_string:
                    date_part = date_string.split('+')[0]
                    posted_date = datetime.datetime.fromisoformat(date_part)
                else:
                    posted_date = datetime.datetime.fromisoformat(date_string)
                
                job_data["Created At"] = posted_date.isoformat()
            except (ValueError, AttributeError) as e:
                logging.warning(f"Errore nell'analisi della data di pubblicazione: {e}")
                # Usa la data corrente meno 30 giorni come fallback
                job_data["Created At"] = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
        
        # URL candidatura
        if "url" in api_response:
            job_data["Company Apply Url"] = api_response["url"]
        else:
            job_data["Company Apply Url"] = job_url
        
        # Industria (se disponibile in qualsiasi campo)
        for field in ["industry", "occupationalCategory"]:
            if field in api_response:
                value = api_response[field]
                if isinstance(value, str):
                    job_data["Industry"] = value
                elif isinstance(value, dict) and "name" in value:
                    job_data["Industry"] = value["name"]
        
        return job_data
    
    # Formato di risposta API standard
    if 'title' in api_response:
        job_data["Title"] = api_response['title']
    
    if 'description' in api_response:
        # Pulisci l'HTML dalla descrizione
        description_html = api_response['description']
        if isinstance(description_html, str):
            if '<' in description_html:
                description_text = BeautifulSoup(description_html, 'html.parser').get_text()
            else:
                description_text = description_html
            
            description_text = re.sub(r'\s+', ' ', description_text).strip()
            job_data["Description"] = description_text
    
    # Posizione
    for field in ['formattedLocation', 'location']:
        if field in api_response and api_response[field]:
            job_data["Location"] = api_response[field]
            break
    
    # Verifica se è remoto
    if job_data["Location"] and not ("remote" in job_data["Location"].lower()):
        if any(remote_keyword in str(api_response).lower() for remote_keyword in ["remote", "remoto", "work from home", "wfh"]):
            job_data["Location"] += " (Remote)"
    
    # Dettagli dell'azienda
    company = api_response.get('companyDetails', {})
    if not company and 'company' in api_response:
        company = api_response['company']
    
    if company:
        # Nome azienda
        for field in ['name', 'companyName', 'displayName']:
            if field in company and company[field]:
                job_data["Company Name"] = company[field]
                break
        
        # Logo
        for field in ['logoUrl', 'logo', 'companyLogo', 'profilePicture']:
            if field in company and company[field]:
                logo = company[field]
                if isinstance(logo, str):
                    job_data["Company Logo"] = logo
                elif isinstance(logo, dict) and 'url' in logo:
                    job_data["Company Logo"] = logo['url']
                break
        
        # Poster ID
        for field in ['companyId', 'id', 'entityUrn']:
            if field in company and company[field]:
                id_value = company[field]
                if isinstance(id_value, str) and ':' in id_value:
                    # Estrai ID da entità URN (es. "urn:li:company:123456")
                    id_match = re.search(r':(\d+)$', id_value)
                    if id_match:
                        job_data["Poster Id"] = id_match.group(1)
                else:
                    job_data["Poster Id"] = str(id_value)
                break
        
        # Se ancora non abbiamo un Poster ID, genera un fallback
        if not job_data["Poster Id"] and job_data["Company Name"]:
            job_data["Poster Id"] = str(abs(hash(job_data["Company Name"])) % 10000000)
        
        # Descrizione azienda
        if 'description' in company:
            job_data["Company Description"] = company['description']
        
        # Sito web
        for field in ['websiteUrl', 'website', 'companyUrl']:
            if field in company and company[field]:
                url = company[field]
                if url.startswith('http'):
                    job_data["Company Website"] = url
                    break
        
        # Industria
        for field in ['industry', 'industries']:
            if field in company:
                value = company[field]
                if isinstance(value, str):
                    job_data["Industry"] = value
                elif isinstance(value, list) and value:
                    job_data["Industry"] = value[0] if isinstance(value[0], str) else str(value[0])
                break
        
        # Numero dipendenti
        if 'employeeCount' in company:
            try:
                count = company['employeeCount']
                if isinstance(count, (int, float)):
                    job_data["Employee Count"] = int(count)
                elif isinstance(count, str):
                    # Estrai numeri da testo come "1,000-5,000 employees"
                    numbers = re.findall(r'\d+', count.replace(',', ''))
                    if numbers:
                        if len(numbers) >= 2:
                            job_data["Employee Count"] = (int(numbers[0]) + int(numbers[1])) // 2
                        else:
                            job_data["Employee Count"] = int(numbers[0])
            except (ValueError, TypeError):
                pass
        
        # Sede
        if 'headquarters' in company:
            hq = company['headquarters']
            if isinstance(hq, str):
                job_data["Headquarters"] = hq
            elif isinstance(hq, dict):
                hq_parts = []
                for field in ['city', 'region', 'country']:
                    if field in hq and hq[field]:
                        hq_parts.append(hq[field])
                if hq_parts:
                    job_data["Headquarters"] = ", ".join(hq_parts)
        
        # Anno fondazione
        if 'foundedYear' in company:
            try:
                value = company['foundedYear']
                if isinstance(value, (int, float)):
                    job_data["Company Founded"] = int(value)
                elif isinstance(value, str) and value.isdigit():
                    job_data["Company Founded"] = int(value)
            except (ValueError, TypeError):
                pass
        
        # Specializzazioni
        if 'specialties' in company:
            specialties = company['specialties']
            if isinstance(specialties, list):
                job_data["Specialties"] = ", ".join(str(s) for s in specialties)
            else:
                job_data["Specialties"] = str(specialties)
    
    # URL candidatura
    for field in ['applyUrl', 'applicationUrl', 'apply_url']:
        if field in api_response and api_response[field]:
            job_data["Company Apply Url"] = api_response[field]
            break
    
    # Data pubblicazione
    if 'listedAt' in api_response:
        try:
            # Converti timestamp (millisecondi) in data ISO
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
    
    # Hiring Manager - impostiamo a null come da schema
    job_data["Hiring Manager Title"] = None
    job_data["Hiring Manager Subtitle"] = None
    job_data["Hiring Manager Title Insight"] = None
    job_data["Hiring Manager Profile"] = None
    job_data["Hiring Manager Image"] = None
    
    return job_data