# Add to linkedin_job_scraper/tests/test_models.py or create if doesn't exist

import unittest
import json
from linkedin_job_scraper.models import (
    SCHEMA, validate_job_data, create_empty_job_data, 
    enrich_job_data_for_application
)
from linkedin_job_scraper.scraper import generate_primary_description, clean_and_validate_job_data
from jsonschema import validate as jsonschema_validate

class TestSchema(unittest.TestCase):
    def test_empty_job_data(self):
        """Test that the empty job data template can be properly enriched and validated"""
        # Create empty job data
        job_data = create_empty_job_data()
        
        # Fill required fields
        job_data["Title"] = "Test Job"
        job_data["Description"] = "This is a test job description"
        job_data["Primary Description"] = "Test Job at Test Company"
        job_data["Detail URL"] = "https://www.linkedin.com/jobs/view/123456789/"
        job_data["Location"] = "Test Location"
        job_data["Poster Id"] = "123456"
        job_data["Company Name"] = "Test Company"
        job_data["Company Description"] = "This is a test company description"
        job_data["Headquarters"] = "Test Headquarters"
        job_data["Created At"] = "2023-01-01T00:00:00"
        job_data["ScrapedAt"] = "2023-01-01T00:00:00"
        
        # Clean and validate
        cleaned_data = clean_and_validate_job_data(job_data)
        
        # Verify validation passes
        self.assertTrue(validate_job_data(cleaned_data))
        
        # Test that it validates against schema
        try:
            jsonschema_validate([cleaned_data], SCHEMA)
            schema_valid = True
        except Exception as e:
            schema_valid = False
            print(f"Schema validation error: {str(e)}")
        
        self.assertTrue(schema_valid)
    
    def test_array_fields(self):
        """Test that array fields are properly handled"""
        job_data = create_empty_job_data()
        
        # Fill required fields
        job_data["Title"] = "Test Job"
        job_data["Description"] = "This is a test job description"
        job_data["Primary Description"] = "Test Job at Test Company"
        job_data["Detail URL"] = "https://www.linkedin.com/jobs/view/123456789/"
        job_data["Location"] = "Test Location"
        job_data["Poster Id"] = "123456"
        job_data["Company Name"] = "Test Company"
        job_data["Company Description"] = "This is a test company description"
        job_data["Headquarters"] = "Test Headquarters"
        job_data["Created At"] = "2023-01-01T00:00:00"
        job_data["ScrapedAt"] = "2023-01-01T00:00:00"
        
        # Test array fields
        job_data["Skill"] = ["Python", "JavaScript", "TypeScript"]
        job_data["Insight"] = ["10 applicants", "Posted 3 days ago"]
        job_data["Specialties"] = ["Web Development", "Frontend", "UI/UX"]
        
        # Clean and validate
        cleaned_data = clean_and_validate_job_data(job_data)
        
        # Verify validation passes
        self.assertTrue(validate_job_data(cleaned_data))
        
        # Check array fields remain arrays
        self.assertIsInstance(cleaned_data["Skill"], list)
        self.assertIsInstance(cleaned_data["Insight"], list)
        self.assertIsInstance(cleaned_data["Specialties"], list)
    
    def test_enrichment(self):
        """Test that job data enrichment works correctly"""
        job_data = create_empty_job_data()
        
        # Fill required fields
        job_data["Title"] = "Senior Angular Developer"
        job_data["Description"] = "We are looking for a TypeScript developer with React experience"
        job_data["Primary Description"] = "Senior Angular Developer at Test Company"
        job_data["Detail URL"] = "https://www.linkedin.com/jobs/view/123456789/"
        job_data["Location"] = "Test Location"
        job_data["Poster Id"] = "123456"
        job_data["Company Name"] = "Test Company"
        job_data["Company Description"] = "This is a test company description"
        job_data["Headquarters"] = "Test Headquarters"
        job_data["Created At"] = "2023-01-01T00:00:00"
        job_data["ScrapedAt"] = "2023-01-01T00:00:00"
        
        # Enrich job data
        enriched_data = enrich_job_data_for_application(job_data)
        
        # Verify Application field exists
        self.assertIn("Application", enriched_data)
        self.assertEqual(enriched_data["Application"]["Status"], "Not Applied")
        
        # Verify Relevance field exists and contains expected data
        self.assertIn("Relevance", enriched_data)
        self.assertTrue(enriched_data["Relevance"]["Angular Mentioned"])
        self.assertTrue(enriched_data["Relevance"]["TypeScript Mentioned"])
        self.assertTrue(enriched_data["Relevance"]["React Mentioned"])
        self.assertIsInstance(enriched_data["Relevance"]["Keywords"], list)
        self.assertGreater(len(enriched_data["Relevance"]["Keywords"]), 0)
        
        # Verify keywords match expected values
        expected_keywords = ["angular", "typescript", "react"]
        for keyword in expected_keywords:
            self.assertIn(keyword, enriched_data["Relevance"]["Keywords"])
    
    def test_primary_description_generation(self):
        """Test that Primary Description is properly generated"""
        job_data = {
            "Title": "Senior Developer",
            "Company Name": "Tech Company",
            "Location": "Remote, Italy",
            "Description": "We're looking for a skilled developer. Must have 5+ years of experience. Competitive salary offered."
        }
        
        primary_desc = generate_primary_description(job_data)
        
        # Verify primary description format
        self.assertIn("Senior Developer at Tech Company", primary_desc)
        self.assertIn("Remote, Italy", primary_desc)
        self.assertIn("We're looking for a skilled developer", primary_desc)
        
    def test_string_to_array_conversion(self):
        """Test that string fields are properly converted to arrays"""
        job_data = create_empty_job_data()
        
        # Fill required fields
        job_data["Title"] = "Test Job"
        job_data["Description"] = "Test description"
        job_data["Primary Description"] = "Test Job at Test Company"
        job_data["Detail URL"] = "https://example.com"
        job_data["Location"] = "Test Location"
        job_data["Poster Id"] = "123"
        job_data["Company Name"] = "Test Company"
        job_data["Company Description"] = "Test company description"
        job_data["Headquarters"] = "Test HQ"
        job_data["Created At"] = "2023-01-01T00:00:00"
        job_data["ScrapedAt"] = "2023-01-01T00:00:00"
        
        # Set string values that should be converted to arrays
        job_data["Specialties"] = "Web Development, UI/UX, Mobile Apps"
        
        # Clean and validate
        cleaned_data = clean_and_validate_job_data(job_data)
        
        # Verify conversion to array
        self.assertIsInstance(cleaned_data["Specialties"], list)
        self.assertEqual(len(cleaned_data["Specialties"]), 3)
        self.assertIn("Web Development", cleaned_data["Specialties"])
        self.assertIn("UI/UX", cleaned_data["Specialties"])
        self.assertIn("Mobile Apps", cleaned_data["Specialties"])

if __name__ == "__main__":
    unittest.main()
