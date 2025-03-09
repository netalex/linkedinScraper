"""
Modelli di dati e schema JSON per LinkedIn Job Scraper.
Definisce la struttura dei dati e le funzioni di validazione.
"""

import logging
import re
# import datetime
from datetime import datetime

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
                "Company Description": {"type": ["string", "null"]},
                "Company Website": {"type": ["string", "null"]},
                "Industry": {"type": ["string", "null"]},
                "Employee Count": {"type": ["integer", "null"]},
                "Headquarters": {"type": ["string", "null"]},
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
                "Poster Id", "Company Name", "Created At", "ScrapedAt"
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
        # Make sure required fields exist
        required_fields = [
            "Title", "Description", "Primary Description", "Detail URL", "Location",
            "Poster Id", "Company Name", "Created At", "ScrapedAt"
        ]
        
        for field in required_fields:
            if field not in job_data or job_data[field] is None or job_data[field] == "":
                # Se il campo è "Company Description", non blocchiamo la validazione
                if field == "Company Description":
                    continue
                logging.error(f"Required field missing or empty: {field}")
                return False
        
        # Check array fields
        array_fields = ["Skill", "Insight", "Specialties"]
        for field in array_fields:
            if field in job_data and job_data[field] is not None:
                if not isinstance(job_data[field], list):
                    logging.error(f"Field {field} should be an array or null, got: {type(job_data[field])}")
                    return False
        
        # Numeric fields
        numeric_fields = ["Employee Count", "Company Founded"]
        for field in numeric_fields:
            if field in job_data and job_data[field] is not None:
                if not isinstance(job_data[field], int):
                    logging.error(f"Field {field} should be an integer or null, got: {type(job_data[field])}")
                    return False
        
        # Date fields
        date_fields = ["Created At", "ScrapedAt"]
        for field in date_fields:
            if field in job_data and job_data[field]:
                try:
                    # Validate ISO format
                    datetime.fromisoformat(job_data[field].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logging.error(f"Field {field} is not a valid ISO date format: {job_data[field]}")
                    return False
        
        # Wrap in array as per schema for full validation
        from jsonschema import validate
        validate([job_data], SCHEMA)
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
        "Company Website": None,  # Changed from None to null
        "Industry": None,  # Changed from None to null
        "Employee Count": None,  # Already null
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
        "Notes": None,
        "Follow Up Date": None,
        "Cover Letter": None,
        "Salary Range": None,
        "Skills Match": None,
        "Location Match": None,
        "Priority": "Medium",
        "Interest Level": "Medium"
    }
    
    # Calculate relevance score based on keywords in title and description
    keywords = ["angular", "typescript", "frontend", "front-end", "front end", "javascript", "react"]
    score = 0
    
    title = enriched_data.get("Title", "").lower()
    description = enriched_data.get("Description", "").lower()
    
    matched_keywords = []
    for keyword in keywords:
        if keyword in title:
            score += 3  # Higher weight for keywords in title
            matched_keywords.append(keyword)
        elif keyword in description:
            score += 1
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)
    
    # Add relevance data
    enriched_data["Relevance"] = {
        "Score": score,
        "Keywords": matched_keywords,
        "Angular Mentioned": "angular" in title.lower() or "angular" in description.lower(),
        "React Mentioned": "react" in title.lower() or "react" in description.lower(),
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