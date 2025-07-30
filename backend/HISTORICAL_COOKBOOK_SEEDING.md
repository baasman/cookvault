# Historical Cookbook Seeding - User Guide

This guide explains how to use the new historical cookbook seeding functionality to populate your CookVault database with recipes from historical cookbook PDFs.

## Overview

The historical cookbook seeding system can:
- Extract text from historical cookbook PDFs
- Segment the text into individual recipes using pattern recognition
- Parse historical recipes with vintage measurement conversions
- Create structured database entries with proper relationships
- Handle historical terminology and cooking methods

## Quick Start

### 1. Basic Usage

To seed the included 1887 Chicago Women's Club cookbook:

```bash
# Dry run (preview without making changes)
cd backend
python -m cookbook_db_utils.cli seed historical-cookbook --dry-run

# Actually create the recipes
python -m cookbook_db_utils.cli seed historical-cookbook
```

### 2. Advanced Options

```bash
# Use custom PDF path
python -m cookbook_db_utils.cli seed historical-cookbook --pdf-path /path/to/cookbook.pdf

# Associate recipes with specific user
python -m cookbook_db_utils.cli seed historical-cookbook --user-id 1

# Clear existing historical data first
python -m cookbook_db_utils.cli seed historical-cookbook --clear

# Development environment
python -m cookbook_db_utils.cli --env development seed historical-cookbook
```

## System Requirements

### Dependencies
- `pdfplumber>=0.10.0` (added to requirements.txt)
- Anthropic API key for recipe parsing
- Redis (optional, for caching)

### Installation
1. Install new dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Ensure your `.env` file has the Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## How It Works

### 1. PDF Text Extraction (`pdf_processor.py`)
- Uses `pdfplumber` for layout-aware text extraction
- Preserves formatting and structure
- Handles page-by-page processing
- Cleans common PDF artifacts

### 2. Recipe Segmentation (`historical_recipe_parser.py`)
- Identifies recipe boundaries using pattern recognition
- Looks for capital letter titles and food-related words
- Segments content into individual recipe blocks
- Estimates difficulty, cooking time, and servings

### 3. Historical Recipe Parsing
- Converts vintage measurements to modern equivalents
- Modernizes historical ingredient names
- Uses Anthropic Claude for intelligent parsing
- Preserves traditional cooking methods

### 4. Database Creation (`historical_cookbook_seeder.py`)
- Creates cookbook entry with historical metadata
- Generates recipe records with ingredients and instructions
- Associates recipes with user accounts
- Handles proper database relationships

## Expected Results

From the 1887 Chicago Women's Club cookbook, you can expect:
- **150+ traditional recipes** from the late 1800s
- **Diverse recipe types**: cakes, pies, meat dishes, preserves, etc.
- **Historical cooking methods**: Traditional techniques and terminology
- **Period measurements**: Automatically converted where possible
- **Cultural significance**: Authentic representation of 19th-century American cooking

## Troubleshooting

### Common Issues

1. **PDF not found**
   ```
   Error: PDF file not found
   ```
   - Check the file path is correct
   - Ensure the PDF file exists in the seed_data directory

2. **No recipes extracted**
   ```
   No recipes could be extracted from the PDF
   ```
   - The PDF might be scanned images (OCR needed)
   - Text extraction failed due to PDF format
   - Recipe patterns not recognized

3. **Anthropic API errors**
   ```
   Recipe parsing failed: API error
   ```
   - Check your Anthropic API key is valid
   - Ensure you have API credits available
   - Verify network connectivity

4. **Database errors**
   ```
   Error creating recipe: Foreign key constraint
   ```
   - Ensure database is properly migrated
   - Check that user accounts exist
   - Run with `--dry-run` to test parsing first

### Debug Options

1. **Dry run mode**: Test parsing without database changes
   ```bash
   python -m cookbook_db_utils.cli seed historical-cookbook --dry-run
   ```

2. **Verbose logging**: Enable detailed output
   ```bash
   python -m cookbook_db_utils.cli --verbose seed historical-cookbook
   ```

3. **Check extraction only**: Test the PDF processor standalone
   ```bash
   cd backend
   python cookbook_db_utils/pdf_processor.py
   ```

## Advanced Configuration

### Custom Historical Cookbooks

To process other historical cookbooks:

1. Place PDF in the seed_data directory
2. Use custom path:
   ```bash
   python -m cookbook_db_utils.cli seed historical-cookbook --pdf-path /path/to/your/cookbook.pdf
   ```

### Measurement Conversions

The system includes conversions for historical measurements:
- `gill` → `1/4 cup`
- `wine glass` → `1/4 cup`
- `tumbler` → `1 cup`
- `saltspoon` → `1/4 teaspoon`
- `dessertspoon` → `2 teaspoons`

### Historical Ingredients

Common historical ingredients are modernized:
- `saleratus` → `baking soda`
- `sweet milk` → `whole milk`
- `graham flour` → `whole wheat flour`
- `indian meal` → `cornmeal`

## Data Structure

### Created Records

Each historical cookbook seeding creates:
- **1 Cookbook record** with historical metadata
- **100+ Recipe records** with vintage context
- **500+ Ingredient records** (shared across recipes)
- **1000+ Instruction records** (step-by-step cooking)
- **Historical tags**: 'historical', '1887', 'traditional', 'vintage'

### Database Schema

Historical recipes include additional metadata:
```json
{
  "historical_metadata": {
    "original_title": "APPLE CUSTARD PIE",
    "era": "1887",
    "source_type": "historical_cookbook",
    "estimated_difficulty": "medium",
    "confidence": 0.85
  }
}
```

## Performance Notes

- **Processing time**: ~5-10 minutes for 150+ recipes
- **Memory usage**: ~100MB peak during processing
- **API calls**: 1 call per recipe to Anthropic Claude
- **Database size**: ~2MB additional data

## Examples

### Sample Recipe Output

Original text:
```
APPLE CUSTARD PIE

Take six large apples, pare and core them, stew them tender, then mash them fine. 
Add the yolks of four eggs, half a cup of sugar, one gill of cream, 
a little nutmeg and cinnamon. Beat all together, put in a pie plate lined with paste, 
and bake half an hour in a moderate oven.
```

Parsed result:
```json
{
  "title": "Apple Custard Pie",
  "ingredients": [
    "6 large apples",
    "4 egg yolks", 
    "1/2 cup sugar",
    "1/4 cup cream",
    "nutmeg to taste",
    "cinnamon to taste"
  ],
  "instructions": [
    "Pare and core 6 large apples, stew them tender, then mash them fine",
    "Add the yolks of 4 eggs, 1/2 cup sugar, 1/4 cup cream, nutmeg and cinnamon",
    "Beat all together",
    "Put in a pie plate lined with pastry and bake 30 minutes in a moderate oven"
  ],
  "cook_time": 30,
  "difficulty": "medium"
}
```

## Contributing

To extend the historical cookbook functionality:

1. **Add new measurement conversions** in `historical_recipe_parser.py`
2. **Improve pattern recognition** in the segmentation logic
3. **Add era-specific parsing** for different time periods
4. **Create specialized processors** for different cookbook formats

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs for detailed error messages
3. Test with `--dry-run` to isolate parsing issues
4. Examine the PDF manually to understand formatting