"""
Modelli di dati e schema JSON per LinkedIn Job Scraper.
Definisce la struttura dei dati e le funzioni di validazione.
"""

import logging
from typing import Dict, Any, List
from jsonschema import validate as jsonschema_validate


# Schema JSON per la validazione
SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "Title": {"type": "string"},
                "Description": {"type": "string"},
                "Primary Description": {"type": "string"},
                "Detail URL": {"type": "string"},
                "Location": {"type": "string"},
                "Skill": {"type": ["array", "null"]},
                "Insight": {"type": ["array", "null"]},
                "Job State": {"type": ["string", "null"]},
                "Poster Id": {"type": "string"},
                "Company Name": {"type": "string"},
                "Company Logo": {"type": ["string", "null"]},
                "Company Apply Url": {"type": ["string", "null"]},
                "Company Description": {"type": "string"},
                "Company Website": {"type": ["string", "null"]},
                "Industry": {"type": ["string", "null"]},
                "Employee Count": {"type": ["integer", "null"]},
                "Headquarters": {"type": "string"},
                "Company Founded": {"type": ["integer", "null"]},
                "Specialties": {"type": ["array", "null"]},
                "Hiring Manager Title": {"type": ["string", "null"]},
                "Hiring Manager Subtitle": {"type": ["string", "null"]},
                "Hiring Manager Title Insight": {"type": ["string", "null"]},
                "Hiring Manager Profile": {"type": ["string", "null"]},
                "Hiring Manager Image": {"type": ["string", "null"]},
                "Created At": {"type": "string"},
                "ScrapedAt": {"type": "string"}
            },
            "required": [
                "Title", "Description", "Primary Description", "Detail URL", "Location",
                "Poster Id", "Company Name", "Company Description", "Headquarters",
                "Created At", "ScrapedAt"
            ]
        }
    ]
}

# Schema per l'arricchimento dei dati con campi per il tracciamento delle candidature
APPLICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "Status": {"type": ["string", "null"]},
        "Applied Date": {"type": ["string", "null"], "format": "date-time"},
        "Response Date": {"type": ["string", "null"], "format": "date-time"},
        "Interview Date": {"type": ["string", "null"], "format": "date-time"},
        "Offer Date": {"type": ["string", "null"], "format": "date-time"},
        "Rejection Date": {"type": ["string", "null"], "format": "date-time"},
        "Notes": {"type": ["string", "null"]},
        "Follow Up Date": {"type": ["string", "null"], "format": "date-time"},
        "Cover Letter": {"type": ["string", "null"]},
        "Salary Range": {"type": ["string", "null"]},
        "Skills Match": {"type": ["integer", "null"]},
        "Location Match": {"type": ["string", "null"]},
        "Priority": {"type": ["string", "null"]},
        "Interest Level": {"type": ["string", "null"]}
    }
}

# Schema per valutare la rilevanza del lavoro
RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "Score": {"type": ["integer", "null"]},
        "Keywords": {"type": ["array", "null"], "items": {"type": "string"}},
        "Angular Mentioned": {"type": ["boolean", "null"]},
        "React Mentioned": {"type": ["boolean", "null"]},
        "TypeScript Mentioned": {"type": ["boolean", "null"]}
    }
}


def validate_job_data(job_data: Dict[str, Any]) -> bool:
    """
    Valida i dati delle offerte di lavoro rispetto allo schema definito.
    
    Args:
        job_data: Dati dell'offerta di lavoro da validare
        
    Returns:
        True se la validazione ha successo, False altrimenti
    """
    try:
        # Avvolgi in un array come richiesto dallo schema
        jsonschema_validate([job_data], SCHEMA)
        return True
    except Exception as e:
        logging.error(f"Validazione dello schema fallita: {str(e)}")
        return False


def create_empty_job_data() -> Dict[str, Any]:
    """
    Crea un template vuoto per i dati di un'offerta di lavoro.
    
    Returns:
        Dizionario con tutti i campi richiesti inizializzati a valori vuoti/predefiniti
    """
    return {
        "Title": "",
        "Description": "",
        "Primary Description": "",  # New required field
        "Detail URL": "",
        "Location": "",
        "Skill": None,  # Changed from None to null
        "Insight": None,  # Changed from None to null
        "Job State": None,  # Changed from "LISTED" to null
        "Poster Id": "",
        "Company Name": "",
        "Company Logo": None,  # Changed from None to null
        "Company Apply Url": None,  # Changed from None to null
        "Company Description": "",
        "Company Website": None,  # Changed from None to null
        "Industry": None,  # Changed from None to null
        "Employee Count": None,  # Already null
        "Headquarters": "",
        "Company Founded": None,  # Already null
        "Specialties": None,  # Changed from string to null
        "Hiring Manager Title": None,  # Already null
        "Hiring Manager Subtitle": None,  # Already null
        "Hiring Manager Title Insight": None,  # Already null
        "Hiring Manager Profile": None,  # Already null
        "Hiring Manager Image": None,  # Already null
        "Created At": None,
        "ScrapedAt": None
    }


def enrich_job_data_for_application(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Arricchisce i dati dell'offerta con campi utili per il tracciamento delle candidature.
    
    Args:
        job_data: Dati originali dell'offerta
        
    Returns:
        Dati arricchiti
    """
    enriched_data = job_data.copy()
    
    # Aggiungi campo dello stato della candidatura
    enriched_data["Application"] = {
        "Status": "Not Applied",
        "Applied Date": None,
        "Response Date": None,
        "Interview Date": None,
        "Offer Date": None,
        "Rejection Date": None,
        "Notes": "",
        "Follow Up Date": None,
        "Cover Letter": None,
        "Salary Range": None,
        "Skills Match": None,
        "Location Match": None,
        "Priority": "Medium",
        "Interest Level": "Medium"
    }
    
    # Aggiungi punteggio di rilevanza basato su parole chiave nel titolo e nella descrizione
    keywords = ["angular", "typescript", "frontend", "front-end", "front end", "javascript"]
    score = 0
    
    title = enriched_data.get("Title", "").lower()
    description = enriched_data.get("Description", "").lower()
    
    for keyword in keywords:
        if keyword in title:
            score += 3  # Peso maggiore per le parole chiave nel titolo
        if keyword in description:
            score += 1
    
    enriched_data["Relevance"] = {
        "Score": score,
        "Keywords": keywords,
        "Angular Mentioned": "angular" in title.lower() or "angular" in description.lower(),
        "TypeScript Mentioned": "typescript" in title.lower() or "typescript" in description.lower()
    }
    
    return enriched_data

# Add to linkedin_job_scraper/scraper.py

def generate_primary_description(job_data: Dict[str, Any]) -> str:
    """
    Generate a concise primary description from job data.
    
    Args:
        job_data: Dictionary containing job data
        
    Returns:
        A concise primary description string
    """
    company = job_data.get("Company Name", "")
    title = job_data.get("Title", "")
    location = job_data.get("Location", "")
    
    # Extract first few sentences from description for a brief summary
    description = job_data.get("Description", "")
    sentences = re.split(r'(?<=[.!?])\s+', description)
    short_desc = " ".join(sentences[:2]) if sentences else ""
    
    # Limit short description length
    if len(short_desc) > 150:
        short_desc = short_desc[:147] + "..."
    
    # Combine into a concise description
    primary_desc = f"{title} at {company}"
    if location:
        primary_desc += f" in {location}"
    
    if short_desc:
        primary_desc += f". {short_desc}"
        
    return primary_desc.strip()