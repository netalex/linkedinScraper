"""
LinkedIn Job Scraper

Uno strumento Python per automatizzare la ricerca e l'analisi di offerte di lavoro su LinkedIn,
con integrazione per Claude AI e sistemi di tracciamento delle candidature.
"""

__version__ = '0.1.0'
__author__ = 'Alessandro Aprile'

from .scraper import scrape_linkedin_job
from .api import extract_job_ids_from_search, try_api_endpoint
from .models import validate_job_data, SCHEMA
from .utils import build_search_url

__all__ = [
    'scrape_linkedin_job',
    'extract_job_ids_from_search',
    'try_api_endpoint',
    'validate_job_data',
    'SCHEMA',
    'build_search_url',
]
