
# LinkedIn Job Scraper Schema Update Guide

This document explains the changes made to the job data schema and how to work with the updated structure.

## Schema Overview

The job data schema has been updated to support more structured data formats and additional fields. Key changes include:

1. Added `Primary Description` as a required field
2. Changed `Skill`, `Insight`, and `Specialties` from string/null to array/null
3. Modified several fields to properly handle null values
4. Updated the `Relevance` schema to include `React Mentioned` flag

## Working with the New Schema

### Required Fields

The following fields are now required:
- `Title`
- `Description`
- `Primary Description` (NEW)
- `Detail URL`
- `Location`
- `Poster Id`
- `Company Name`
- `Company Description`
- `Headquarters`
- `Created At`
- `ScrapedAt`

### Array Fields

The following fields are now arrays (or null):
- `Skill`: Array of skills required for the job
- `Insight`: Array of additional insights about the job
- `Specialties`: Array of company specialties

### Primary Description

The `Primary Description` field contains a concise summary of the job, formatted as:
```
{Job Title} at {Company Name} in {Location}. {Brief description}
```

This field is automatically generated from other job data fields but can be manually set if needed.

## Schema Validation

The updated code includes comprehensive validation to ensure all data conforms to the schema:

1. Required fields are checked for existence and content
2. Array fields are validated for correct type
3. Numeric fields are validated to be integers or null
4. Date fields are validated to be in proper ISO format

## Application and Relevance Schemas

The `Application` schema is used for tracking job applications with fields like status, dates, and priority.

The `Relevance` schema helps determine job relevance to your skills with:
- Score (numeric relevance score)
- Keywords (matched keywords)
- Angular/React/TypeScript mentioned flags

## Working with Legacy Data

If you have data scraped with the old schema, you'll need to update it to the new format. Key transformations:
- Generate `Primary Description` field
- Convert string `Specialties` to arrays
- Add proper null values where empty strings were used
- Add the React Mentioned flag to the Relevance schema

## Example Usage

```python
from linkedin_job_scraper.models import validate_job_data, create_empty_job_data
from linkedin_job_scraper.scraper import scrape_linkedin_job, generate_primary_description

# Create job data
job_data = scrape_linkedin_job("https://www.linkedin.com/jobs/view/123456789/")

# Validate against schema
if validate_job_data(job_data):
    print("Job data is valid")
else:
    print("Job data is invalid")

# Access array fields
if job_data["Skill"]:
    print(f"Required skills: {', '.join(job_data['Skill'])}")

# Create clean job data template
new_job = create_empty_job_data()
new_job["Title"] = "Senior Developer"
# ... fill other required fields
new_job["Primary Description"] = generate_primary_description(new_job)

```


## Testing the Schema Implementation

We've added comprehensive tests to verify schema compliance. These tests are located in `linkedin_job_scraper/tests/test_models.py`.

### Running the Tests

To run the tests and verify your implementation:

1. Make sure you have the testing dependencies installed:
   ```bash
   pip install pytest
   ```

2. Run the tests using pytest:
   ```bash
   # From the project root directory
   pytest linkedin_job_scraper/tests/test_models.py -v
   ```

3. Or run the test file directly:
   ```bash
   # From the project root directory
   python -m linkedin_job_scraper.tests.test_models
   ```

### What the Tests Verify

The tests check several aspects of the schema implementation:

1. **Basic Schema Validation**: Verifies that a correctly populated job data structure passes validation
2. **Array Fields Handling**: Ensures that `Skill`, `Insight`, and `Specialties` are properly handled as arrays
3. **Data Enrichment**: Tests the job data enrichment with application tracking and relevance scoring
4. **Primary Description Generation**: Validates the format and content of the automatically generated descriptions
5. **String to Array Conversion**: Confirms that string fields are properly converted to arrays when needed

### Adding Your Own Tests

You can extend the test suite to include your specific use cases:

```python
def test_your_custom_scenario(self):
    """Test description"""
    # Setup test data
    job_data = create_empty_job_data()
    job_data["Title"] = "Your Test Job"
    # Fill other required fields...
    
    # Run the function you want to test
    result = your_function(job_data)
    
    # Assert expected outcomes
    self.assertEqual(expected_value, result)
```

### Troubleshooting Common Test Failures

If tests fail, check these common issues:

1. **Schema Validation Failures**: Ensure all required fields are filled and have the correct data types
2. **Array Field Issues**: Check that array fields are actually lists, not strings
3. **Date Format Problems**: Make sure dates are in ISO format
4. **Null Values**: Verify that null values are represented as `None`, not empty strings or other values


