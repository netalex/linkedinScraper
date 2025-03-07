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
                "Detail URL": {"type": "string"},
                "Location": {"type": "string"},
                "Skill": {"type": "null"},
                "Insight": {"type": "null"},
                "Job State": {"type": "string"},
                "Poster Id": {"type": "string"},
                "Company Name": {"type": "string"},
                "Company Logo": {"type": "string"},
                "Company Apply Url": {"type": "string"},
                "Company Description": {"type": "string"},
                "Company Website": {"type": "string"},
                "Industry": {"type": "string"},
                "Employee Count": {"type": "integer"},
                "Headquarters": {"type": "string"},
                "Company Founded": {"type": "integer"},
                "Specialties": {"type": "string"},
                "Hiring Manager Title": {"type": "null"},
                "Hiring Manager Subtitle": {"type": "null"},
                "Hiring Manager Title Insight": {"type": "null"},
                "Hiring Manager Profile": {"type": "null"},
                "Hiring Manager Image": {"type": "null"},
                "Created At": {"type": "string"},
                "ScrapedAt": {"type": "string"}
            },
            "required": [
                "Title", "Description", "Detail URL", "Location", "Skill", "Insight",
                "Job State", "Poster Id", "Company Name", "Company Logo", "Company Apply Url",
                "Company Description", "Company Website", "Industry", "Employee Count",
                "Headquarters", "Company Founded", "Specialties", "Hiring Manager Title",
                "Hiring Manager Subtitle", "Hiring Manager Title Insight", "Hiring Manager Profile",
                "Hiring Manager Image", "Created At", "ScrapedAt"
            ]
        }
    ]
}

# Schema per l'arricchimento dei dati con campi per il tracciamento delle candidature
APPLICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "Status": {"type": "string"},
        "Applied Date": {"type": ["string", "null"]},
        "Response Date": {"type": ["string", "null"]},
        "Interview Date": {"type": ["string", "null"]},
        "Offer Date": {"type": ["string", "null"]},
        "Rejection Date": {"type": ["string", "null"]},
        "Notes": {"type": "string"},
        "Follow Up Date": {"type": ["string", "null"]},
        "Cover Letter": {"type": ["string", "null"]},
        "Salary Range": {"type": ["string", "null"]},
        "Skills Match": {"type": ["integer", "null"]},
        "Location Match": {"type": ["string", "null"]},
        "Priority": {"type": "string"},
        "Interest Level": {"type": "string"}
    }
}

# Schema per valutare la rilevanza del lavoro
RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "Score": {"type": "integer"},
        "Keywords": {"type": "array", "items": {"type": "string"}},
        "Angular Mentioned": {"type": "boolean"},
        "TypeScript Mentioned": {"type": "boolean"}
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
        "Title": None,
        "Description": None,
        "Detail URL": None,
        "Location": None,
        "Skill": None,
        "Insight": None,
        "Job State": "LISTED",  # Valore predefinito
        "Poster Id": None,
        "Company Name": None,
        "Company Logo": None,
        "Company Apply Url": None,
        "Company Description": None,
        "Company Website": None,
        "Industry": None,
        "Employee Count": None,
        "Headquarters": None,
        "Company Founded": None,
        "Specialties": None,
        "Hiring Manager Title": None,
        "Hiring Manager Subtitle": None,
        "Hiring Manager Title Insight": None,
        "Hiring Manager Profile": None,
        "Hiring Manager Image": None,
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
