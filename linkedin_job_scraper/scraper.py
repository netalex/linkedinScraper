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
import os
from typing import Dict, Any, List, Optional, Tuple, Union

from bs4 import BeautifulSoup

from .utils import extract_job_id_from_url, make_request_with_backoff, get_request_headers
from .api import try_api_endpoint, extract_job_ids_from_search
from .models import validate_job_data, create_empty_job_data, enrich_job_data_for_application


# Debug utility function
def save_debug_html(html_content, job_id):
    """Save HTML content for debugging purposes."""
    try:
        debug_dir = "debug_html"
        os.makedirs(debug_dir, exist_ok=True)
        with open(f"{debug_dir}/job_{job_id}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"Saved debug HTML for job {job_id}")
    except Exception as e:
        logging.error(f"Failed to save debug HTML: {e}")


def clean_description_text(text):
    """Clean and format job description text."""
    if not text:
        return "No description available"
    
    # Remove multiple whitespaces and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common LinkedIn UI text like "Show more" or "Show less"
    text = re.sub(r'Show\s+(more|less)', '', text)
    
    # Remove other UI elements that might be captured
    text = re.sub(r'Apply on company site', '', text)
    text = re.sub(r'Save', '', text)
    
    return text.strip()


# List of all possible selectors for job descriptions
DESCRIPTION_SELECTORS = [
    'div.description__text',
    'div.show-more-less-html__markup',
    'div.jobs-description-content__text',
    'div.job-details-jobs-unified-description__container',
    'div[data-job-description]',
    'section.description',
    'div.job-description',
    # More specific selectors
    'div.jobs-box__html-content',
    'div.jobs-unified-top-card__description-container',
    'div.jobs-unified-description__content',
    '.jobs-description__content',
    'div.jobs-description-details',
    'div.jobs-description__details',
    # LinkedIn 2023-2025 selectors
    'article[data-job-description]',
    'div.jobs-description',
    'div.job-view-layout',
    'section.jobs-description',
    # Broader fallback selectors
    'div[class*="description"]',
    'div[class*="job-description"]',
    'article.description'
]


def extract_description_from_html(soup, job_url):
    """
    Try multiple approaches to extract job description from HTML.
    
    Args:
        soup: BeautifulSoup object of the job page
        job_url: URL of the job posting
        
    Returns:
        Extracted description text
    """
    # Try with specific selectors first
    for selector in DESCRIPTION_SELECTORS:
        description_element = soup.select_one(selector)
        if description_element:
            text = description_element.get_text(" ", strip=True)
            if text and len(text) > 50:  # Filter out too short texts
                return clean_description_text(text)
    
    # Try extracting from JSON-LD structured data
    json_ld = soup.select_one('script[type="application/ld+json"]')
    if json_ld:
        try:
            data = json.loads(json_ld.string)
            if "description" in data:
                return clean_description_text(data["description"])
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # Try finding description in attributes
    for attr in ['content', 'data-description', 'description']:
        elements = soup.select(f'[{attr}]')
        for element in elements:
            if attr in element.attrs and len(element[attr]) > 100:
                return clean_description_text(element[attr])
    
    # Fallback: try to extract from any large text section after the title
    main_content = soup.select_one('main') or soup.select_one('body')
    if main_content:
        paragraphs = main_content.find_all(['p', 'div', 'span', 'li'], class_=lambda c: c and ('description' in c.lower() or 'detail' in c.lower()))
        if paragraphs:
            combined_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
            if len(combined_text) > 100:
                return clean_description_text(combined_text)
    
    # Last resort: look for any containers with "Show more" buttons (common in LinkedIn)
    show_more_containers = soup.select('[class*="show-more"]')
    if show_more_containers:
        for container in show_more_containers:
            parent = container.parent
            if parent and len(parent.get_text(strip=True)) > 100:  # Longer text is likely description
                return clean_description_text(parent.get_text(strip=True))
    
    return "No description available"


def extract_data_from_html(html_content: str, job_url: str) -> Dict[str, Any]:
    """
    Estrae i dati dell'offerta dal contenuto HTML di una pagina di offerta di lavoro LinkedIn.
    
    Args:
        html_content: Contenuto HTML della pagina dell'offerta
        job_url: URL dell'offerta
        
    Returns:
        Dizionario contenente i dati estratti dell'offerta
    """
    job_id = extract_job_id_from_url(job_url) or "unknown"
    
    # Save HTML for debugging
    save_debug_html(html_content, job_id)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Inizializza con i campi richiesti
    job_data = create_empty_job_data()
    job_data["Detail URL"] = job_url
    job_data["ScrapedAt"] = datetime.datetime.now().isoformat()
    
    # Estrai il titolo dell'offerta
    title_selectors = [
        'h1.top-card-layout__title',
        'h1.job-details-jobs-unified-top-card__job-title',
        'h1.topcard__title',
        'h1.jobs-unified-top-card__job-title',
        'h1[data-test-job-title]',
        'h2.t-24',
        'h2.job-title'
        'h1.job-title',
        '.job-view-layout h1',
        '.jobs-unified-top-card__content h1',
        'h1.artdeco-entity-lockup__title'
        # New selectors based on examples
        'h2.top-card-layout__title',                              # From your first example
        '.topcard__title',                                        # Generic class
        '.topcard__link h2',                                      # Parent-child selector
        'a[data-tracking-control-name="public_jobs_topcard-title"] h2',  # Attribute-based

        # Search results page selectors
        'a.base-card__full-link span.sr-only',                    # From your second example
        '[data-tracking-control-name="public_jobs_jserp-result_search-card"] span.sr-only',
        '.base-card__full-link span.sr-only',                     # Simplified version

        # More general selectors to try
        '[class*="title"]',                                       # Any element with 'title' in class
        'h1, h2',                                                 # Any h1 or h2 element
    ]
    
    # Initialize the title
    job_data["Title"] = "Offerta senza titolo"  # Default title

    # Try all title selectors
    for selector in title_selectors:
        title_elements = soup.select(selector)
        for title_element in title_elements:
            title_text = title_element.get_text(strip=True)
            if title_text and len(title_text) > 5:  # Ensure it's not empty or too short
                job_data["Title"] = title_text
                # Once we find a valid title, break out of this selector loop
                break
        # If we found a title with this selector, break out of the outer loop
        if job_data["Title"] != "Offerta senza titolo":
            break
    
    # Additional fallbacks if we still don't have a good title
    if job_data["Title"] == "Offerta senza titolo":
        # Try META tags
        for meta_selector in ['meta[property="og:title"]', 'meta[name="title"]', 'title']:
            meta_element = soup.select_one(meta_selector)
            if meta_element:
                if meta_selector == 'title':
                    title_text = meta_element.get_text(strip=True)
                else:
                    title_text = meta_element.get('content', '')
                    
                if title_text:
                    # Clean up typical LinkedIn title format "Job Title | Company | LinkedIn"
                    for separator in [' | LinkedIn', ' - LinkedIn', ' at ', ' | ']:
                        if separator in title_text:
                            title_text = title_text.split(separator)[0].strip()
                            
                    if title_text and len(title_text) > 5:
                        job_data["Title"] = title_text
                        break

    
    # Extract description using our enhanced approach
    job_data["Description"] = extract_description_from_html(soup, job_url)
    
    # If description extraction failed, try direct API approach as fallback
    if not job_data["Description"] or job_data["Description"] == "No description available":
        api_description = get_job_details_from_api(job_id)
        if api_description:
            job_data["Description"] = api_description
    
    # Estrai la posizione
    location_selectors = [
        'span.topcard__flavor--bullet',
        'span.job-details-jobs-unified-top-card__bullet',
        'span.job-info__location',
        '.jobs-unified-top-card__bullet',
        '.jobs-unified-top-card__location',
        '.job-details-jobs-unified-top-card__primary-description-container span'
    ]
    
    for selector in location_selectors:
        location_element = soup.select_one(selector)
        if location_element:
            job_data["Location"] = location_element.get_text().strip()
            break
    
    # Estrai il nome dell'azienda
    company_selectors = [
        'a.topcard__org-name-link',
        'a.job-details-jobs-unified-top-card__company-name',
        'span.topcard__flavor--bullet ~ span.topcard__flavor',
        '.jobs-unified-top-card__company-name',
        '[data-tracking-control-name="public_jobs_topcard-org-name"]'
    ]
    
    for selector in company_selectors:
        company_element = soup.select_one(selector)
        if company_element:
            job_data["Company Name"] = company_element.get_text().strip()
            break
    
    # Estrai il logo dell'azienda
    logo_selectors = [
        'img.artdeco-entity-image',
        'img.lazy-image',
        'img.jobs-company-logo',
        'img.jobs-unified-top-card__company-logo'
    ]
    
    for selector in logo_selectors:
        logo_element = soup.select_one(selector)
        if logo_element and 'src' in logo_element.attrs:
            job_data["Company Logo"] = logo_element['src']
            break
    
    # Estrai l'URL per candidarsi
    apply_selectors = [
        'a.apply-button',
        'a[data-tracking-control-name="public_jobs_apply-link-offsite_sign-in"]',
        'a[data-control-name="view_application"]',
        'a[data-job-id]'
    ]
    
    for selector in apply_selectors:
        apply_button = soup.select_one(selector)
        if apply_button and 'href' in apply_button.attrs:
            job_data["Company Apply Url"] = apply_button['href']
            break
    
    if not job_data["Company Apply Url"]:
        job_data["Company Apply Url"] = f"https://www.linkedin.com/job-apply/{job_url.split('/')[-1].split('?')[0]}"
    
    # Estrai descrizione dell'azienda
    company_desc_selectors = [
        'div.company-description',
        'div.topcard__org-description',
        'div.jobs-company-description',
        'p.topcard__flavor--metadata'
    ]
    
    for selector in company_desc_selectors:
        company_about = soup.select_one(selector)
        if company_about:
            job_data["Company Description"] = company_about.get_text().strip()
            break
    
    # Website dell'azienda
    website_selectors = [
        'a[href*="://"].link-without-visited-state',
        'a[data-tracking-control-name="public_jobs_topcard-org-name"]',
        'a.ember-view.org-top-card-primary-actions__action'
    ]
    
    for selector in website_selectors:
        company_website_element = soup.select_one(selector)
        if company_website_element and 'href' in company_website_element.attrs:
            href = company_website_element['href']
            if href.startswith('http') and 'linkedin.com' not in href:
                job_data["Company Website"] = href
                break
    
    # Estrai altre informazioni sull'azienda
    company_details = soup.select('dd.top-card-layout__card-elements, .jobs-company-info dd, .jobs-unified-top-card__job-insight')
    
    for detail in company_details:
        text = detail.get_text().strip().lower()
        
        if "employees" in text:
            # Estrai numero di dipendenti
            numbers = re.findall(r'\d+[,\.]?\d*', text.replace(',', ''))
            if numbers:
                try:
                    if len(numbers) >= 2:
                        job_data["Employee Count"] = (int(float(numbers[0])) + int(float(numbers[1]))) // 2
                    else:
                        job_data["Employee Count"] = int(float(numbers[0]))
                except (ValueError, TypeError):
                    pass
        elif "headquarters" in text:
            job_data["Headquarters"] = text.replace("headquarters:", "").strip()
        elif "industry" in text:
            job_data["Industry"] = text.replace("industry:", "").strip()
        elif "founded" in text:
            year_match = re.search(r'\b\d{4}\b', text)
            if year_match:
                try:
                    job_data["Company Founded"] = int(year_match.group(0))
                except ValueError:
                    pass
    
    # Estrai specialties se disponibili
    specialties_selectors = [
        'div.specialties',
        'div.org-add-specialities',
        '.company-specialties'
    ]
    
    for selector in specialties_selectors:
        specialties_element = soup.select_one(selector)
        if specialties_element:
            job_data["Specialties"] = specialties_element.get_text().strip()
            break
    
    # Estrai poster ID se disponibile
    poster_selectors = [
        '[data-poster-id]',
        '[data-job-poster-id]',
        'a[data-control-name="job_card_company"]'
    ]
    
    for selector in poster_selectors:
        poster_element = soup.select_one(selector)
        if poster_element:
            for attr in ['data-poster-id', 'data-job-poster-id', 'data-company-id']:
                if attr in poster_element.attrs:
                    job_data["Poster Id"] = poster_element[attr]
                    break
            if job_data["Poster Id"]:
                break
    
    # Fallback: genera Poster ID dal nome dell'azienda
    if not job_data["Poster Id"] and job_data["Company Name"]:
        job_data["Poster Id"] = str(abs(hash(job_data["Company Name"])) % 10000000)
    
    # Estrai data di pubblicazione
    posted_selectors = [
        'span.posted-date',
        'span.job-details-jobs-unified-top-card__posted-date',
        'span.job-details-jobs-unified-top-card__subtitle-secondary-grouping span',
        '.jobs-unified-top-card__posted-date',
        '.job-details-jobs-unified-top-card__subtitle-secondary-grouping'
    ]
    
    for selector in posted_selectors:
        posted_date_element = soup.select_one(selector)
        if posted_date_element:
            posted_text = posted_date_element.get_text().strip()
            
            # Use the parse_posted_date function to extract and standardize the date
            created_date = parse_posted_date(posted_text)
            if created_date:
                job_data["Created At"] = created_date
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
    
    # Imposta lo stato dell'offerta
    job_data["Job State"] = "LISTED"
    
    # Imposta i campi null richiesti dallo schema
    job_data["Skill"] = None
    job_data["Insight"] = None
    
    return job_data


def get_job_details_from_api(job_id):
    """
    Try to get job details directly from LinkedIn's API endpoint.
    
    Args:
        job_id: LinkedIn job ID
        
    Returns:
        Description text if successful, None otherwise
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = get_request_headers()
    
    # More API-friendly headers
    headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
    headers['X-Requested-With'] = 'XMLHttpRequest'
    
    try:
        response_text = make_request_with_backoff(url, headers)
        if not response_text:
            return None
        
        # Save debug HTML
        save_debug_html(response_text, f"{job_id}_api")
        
        # LinkedIn may return HTML instead of JSON
        soup = BeautifulSoup(response_text, 'html.parser')
        
        # Try to extract from description section
        description = extract_description_from_html(soup, url)
        if description and description != "No description available":
            return description
        
        # Try to extract from JSON-LD
        json_ld = soup.select_one('script[type="application/ld+json"]')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if "description" in data:
                    return clean_description_text(data["description"])
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Try to find description in the response itself if it looks like JSON
        try:
            if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                data = json.loads(response_text)
                if "description" in data:
                    desc_text = data["description"]
                    if isinstance(desc_text, str):
                        # Clean up HTML from description
                        if '<' in desc_text and '>' in desc_text:
                            desc_soup = BeautifulSoup(desc_text, 'html.parser')
                            desc_text = desc_soup.get_text(" ", strip=True)
                        return clean_description_text(desc_text)
        except (json.JSONDecodeError, TypeError):
            pass
            
    except Exception as e:
        logging.error(f"Error in get_job_details_from_api: {str(e)}")
    
    return None


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
    # Check if we received HTML instead of JSON
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


def scrape_linkedin_job(job_url: str, min_delay: int = 1, max_delay: int = 3,
                       proxy_url: str = None) -> Optional[Dict[str, Any]]:
    """
    Scrape a LinkedIn job posting and return the data in the required format.
    
    Args:
        job_url: URL of the LinkedIn job posting
        min_delay: Minimum delay before API request in seconds
        max_delay: Maximum delay before API request in seconds
        proxy_url: Proxy URL to use for requests
        
    Returns:
        Dictionary containing job data if successful, None otherwise
    """
    job_id = extract_job_id_from_url(job_url)
    if not job_id:
        logging.error(f"Impossibile estrarre l'ID dell'offerta dall'URL: {job_url}")
        return None
    
    logging.info(f"ID offerta estratto: {job_id}")
    
    # First, try using the API endpoint
    api_response = try_api_endpoint(job_id, min_delay, max_delay, proxy_url)
    if api_response:
        logging.info("Dati recuperati con successo dall'endpoint API")
        job_data = extract_data_from_api_response(api_response, job_url)
    else:
        logging.info("Failed to retrieve data from API endpoint, falling back to HTML scraping")
        # Fall back to scraping the HTML page
        headers = get_request_headers()
        html_content = make_request_with_backoff(job_url, headers, proxy_url=proxy_url)
        if not html_content:
            logging.error("Impossibile recuperare il contenuto HTML")
            return None
        
        # Save HTML for debugging
        save_debug_html(html_content, job_id)
        
        job_data = extract_data_from_html(html_content, job_url)
    
    # Valida e pulisci i dati
    if not validate_job_data(job_data):
        logging.warning("I dati dell'offerta non sono conformi allo schema, tentativo di correzione...")
        # Tentativo di correggere problemi comuni con i dati
        job_data = clean_and_validate_job_data(job_data)
        
        if not validate_job_data(job_data):
            logging.error("Impossibile validare i dati dell'offerta anche dopo la pulizia")
    
    # Arricchisci con campi per il tracciamento delle candidature se necessario
    job_data = enrich_job_data_for_application(job_data)
    
    return job_data


def clean_and_validate_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pulisce e valida i dati dell'offerta per garantire la conformità allo schema.
    
    Args:
        job_data: Dati grezzi dell'offerta
        
    Returns:
        Dati dell'offerta puliti e validati
    """
    cleaned_data = job_data.copy()
    
    # Imposta valori predefiniti per i campi obbligatori che potrebbero mancare
    if cleaned_data["Title"] is None:
        cleaned_data["Title"] = "Offerta senza titolo"
    
    if cleaned_data["Description"] is None:
        cleaned_data["Description"] = "Nessuna descrizione disponibile"
    
    if cleaned_data["Location"] is None:
        cleaned_data["Location"] = "Remote"
    
    if cleaned_data["Company Name"] is None:
        cleaned_data["Company Name"] = "Azienda sconosciuta"
    
    if cleaned_data["Industry"] is None:
        cleaned_data["Industry"] = "Information Technology"
    
    if cleaned_data["Headquarters"] is None:
        cleaned_data["Headquarters"] = "Sconosciuta"
    
    if cleaned_data["Specialties"] is None:
        cleaned_data["Specialties"] = "Non specificato"
    
    if cleaned_data["Poster Id"] is None:
        cleaned_data["Poster Id"] = "000000"
    
    if cleaned_data["Company Logo"] is None:
        cleaned_data["Company Logo"] = "https://static.licdn.com/aero-v1/sc/h/dbvmk0tsk0o0hd59fi64z3own"
    
    if cleaned_data["Company Apply Url"] is None:
        cleaned_data["Company Apply Url"] = cleaned_data["Detail URL"]
    
    if cleaned_data["Company Website"] is None:
        cleaned_data["Company Website"] = "https://www.linkedin.com/"
    
    if cleaned_data["Company Description"] is None:
        cleaned_data["Company Description"] = "Nessuna descrizione dell'azienda disponibile"
    
    # Assicurati che Created At sia una stringa di data in formato ISO valida
    if cleaned_data["Created At"] is None:
        # Se non abbiamo una data di creazione, usa 30 giorni fa come predefinito
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        cleaned_data["Created At"] = thirty_days_ago.isoformat()
    
    # Assicurati che Employee Count sia un intero
    if cleaned_data["Employee Count"] is not None:
        try:
            cleaned_data["Employee Count"] = int(cleaned_data["Employee Count"])
        except (ValueError, TypeError):
            cleaned_data["Employee Count"] = None
    
    # Assicurati che Company Founded sia un intero
    if cleaned_data["Company Founded"] is not None:
        try:
            cleaned_data["Company Founded"] = int(cleaned_data["Company Founded"])
        except (ValueError, TypeError):
            cleaned_data["Company Founded"] = None
    
    return cleaned_data


def process_search_results(search_url: str, output_file: str, max_jobs: int = 100,
                          min_delay: int = 2, max_delay: int = 5,
                          proxy_url: str = None) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Elabora i risultati di ricerca di lavoro di LinkedIn.
    
    Args:
        search_url: URL di ricerca lavoro di LinkedIn
        output_file: Percorso del file di output per i dati JSON
        max_jobs: Numero massimo di offerte da scrapare
        min_delay: Ritardo minimo tra le richieste
        max_delay: Ritardo massimo tra le richieste
        proxy_url: URL del proxy da utilizzare per le richieste
        
    Returns:
        Tupla di (successo, lista_dati_offerte)
    """
    logging.info(f"Elaborazione dei risultati di ricerca dall'URL: {search_url}")
    
    # Estrai gli ID delle offerte dai risultati di ricerca
    job_ids = extract_job_ids_from_search(search_url, max_jobs, min_delay, max_delay, proxy_url)
    
    if not job_ids:
        logging.error("Nessun ID offerta trovato nei risultati di ricerca")
        return False, []
    
    logging.info(f"Trovati {len(job_ids)} ID offerta da elaborare")
    
    # Scraping di ogni offerta
    all_jobs_data = []
    
    try:
        from tqdm import tqdm
        job_ids_iter = tqdm(job_ids, desc="Scraping offerte di lavoro")
    except ImportError:
        logging.warning("Package tqdm non installato. Nessuna progress bar disponibile.")
        job_ids_iter = job_ids
    
    for i, job_id in enumerate(job_ids_iter):
        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        logging.info(f"Elaborazione offerta {i+1}/{len(job_ids)}: {job_url}")
        
        # Ritardo casuale prima di ogni richiesta
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        
        job_data = scrape_linkedin_job(job_url, min_delay, max_delay, proxy_url)
        if job_data:
            all_jobs_data.append(job_data)
            logging.info(f"Scraping offerta completato con successo: {job_data['Title']} presso {job_data['Company Name']}")
        else:
            logging.warning(f"Impossibile effettuare lo scraping dell'offerta con ID {job_id}")
    
    if not all_jobs_data:
        logging.error("Impossibile effettuare lo scraping di alcuna offerta")
        return False, []
    
    # Salva nel file JSON
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_jobs_data, f, indent=2, ensure_ascii=False)
        logging.info(f"Salvate {len(all_jobs_data)} offerte di lavoro in {output_file}")
        return True, all_jobs_data
    except Exception as e:
        logging.error(f"Errore nel salvataggio dei dati delle offerte nel file: {str(e)}")
        return False, all_jobs_data


def cleanup_debug_files(keep_last_n: int = 5) -> None:
    """
    Pulisce i file HTML di debug, mantenendo solo gli ultimi N.
    
    Args:
        keep_last_n: Numero di file da mantenere
    """
    import os
    import glob
    import re
    
    try:
        # Trova tutti i file di debug
        debug_files = glob.glob("debug_html/job_*.html")
        if not debug_files:
            return
            
        # Ordina per data di creazione (più recente per ultimo)
        debug_files.sort(key=lambda f: os.path.getmtime(f))
        
        # Mantieni solo gli ultimi N
        files_to_delete = debug_files[:-keep_last_n] if keep_last_n > 0 else debug_files
        
        # Elimina i file
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except Exception as e:
                logging.warning(f"Impossibile eliminare {file_path}: {e}")
        
        logging.info(f"Eliminati {len(files_to_delete)} file HTML di debug")
    except Exception as e:
        logging.warning(f"Errore durante la pulizia dei file di debug: {e}")