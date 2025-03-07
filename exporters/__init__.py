"""
Package per l'esportazione dei dati di LinkedIn Job Scraper.
Fornisce moduli per l'esportazione in vari formati e l'integrazione con altri sistemi.
"""

from .json_exporter import (
    save_job_data_to_json,
    save_jobs_data_to_json,
    export_individual_job_files,
    create_jobs_index
)

from .claude_exporter import prepare_claude_prompt

__all__ = [
    'save_job_data_to_json',
    'save_jobs_data_to_json',
    'export_individual_job_files',
    'create_jobs_index',
    'prepare_claude_prompt'
]
