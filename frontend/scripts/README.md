# Recipe Import Script

This script imports LaTeX recipes from the [drewnutt/CookBook](https://github.com/drewnutt/CookBook) GitHub repository using the backend's AI parsing system for maximum accuracy.

## Features

- 🔍 **Automatic Discovery**: Crawls the GitHub repository to find all `.tex` recipe files
- 🧠 **AI-Powered Parsing**: Uses the backend's Claude AI model for accurate recipe extraction
- 🔄 **Retry Logic**: Automatically retries failed requests with exponential backoff
- 💾 **Progress Saving**: Saves progress periodically and supports resuming interrupted imports
- 📊 **Detailed Reporting**: Provides comprehensive statistics and error reporting
- 🏷️ **Category Organization**: Preserves recipe categories (Bread, Dessert, etc.)

## Requirements

- Python 3.7+
- `requests` library (`pip install requests`)
- Valid authentication token for the cookbook API
- Backend server with the new `/api/recipes/upload-text` endpoint

## Setup

1. Install dependencies:
```bash
pip install requests
```

2. Get your authentication token:
   - Log into your cookbook application
   - Extract your JWT token from browser dev tools or API calls

3. Set environment variables:
```bash
export AUTH_TOKEN="your_jwt_token_here"
export API_URL="http://localhost:5000"  # Optional, defaults to localhost:5000
```

## Usage

### Basic Import

```bash
python import_recipes.py
```

This will:
- Find all recipe files in the GitHub repository
- Create a new cookbook called "Imported LaTeX Cookbook"
- Import all recipes using AI parsing
- Save detailed results to `import_results.json`

### Resume Interrupted Import

If an import is interrupted, you can resume from where it left off:

```bash
# The script automatically saves progress every 5 recipes
# Just run the script again and it will resume automatically
python import_recipes.py
```

### Advanced Configuration

You can modify the script to customize:

- Cookbook title and metadata
- Retry attempts and delays
- Progress saving frequency
- API endpoints

## Output Files

- `import_results.json` - Detailed import statistics and error log
- `import_progress.json` - Progress tracking file for resume functionality

## Example Output

```
Starting recipe import process...
Found recipe directory: Bread
Found recipe directory: Breakfast
...
Total recipe files found: 127

Creating cookbook: Imported LaTeX Cookbook
Created cookbook with ID: 42

[1/127] Processing Bread/aloo_paratha.tex
  ✅ Successfully imported: Aloo Paratha

[2/127] Processing Bread/corn_tortillas.tex
  ✅ Successfully imported: Corn Tortillas

...

==================================================
IMPORT SUMMARY
==================================================
Total recipes found: 127
Successfully imported: 125
Failed imports: 2

Detailed results saved to: import_results.json
```

## Troubleshooting

### Authentication Errors
- Ensure your `AUTH_TOKEN` is valid and not expired
- Check that the token has proper permissions to create recipes

### Network Errors
- The script includes retry logic for temporary network issues
- Check your internet connection and API server availability

### Recipe Parsing Issues
- Some LaTeX recipes may have unusual formatting that confuses the AI
- Check the error log in `import_results.json` for specific parsing failures
- The AI model is quite robust and handles most LaTeX variations well

### Server Overload
- The script includes a 1-second delay between requests
- If the server is still overwhelmed, you can increase the delay in the code

## Script Architecture

### Components

1. **GitHubCrawler**: Discovers and downloads recipe files from the repository
2. **LaTeXProcessor**: Cleans and prepares LaTeX content for AI parsing
3. **RecipeUploader**: Handles API communication with retry logic
4. **RecipeImporter**: Orchestrates the entire import process

### AI Processing Flow

1. **Download**: Raw LaTeX file content from GitHub
2. **Clean**: Convert LaTeX commands to readable text
3. **Enhance**: Add category context for better AI understanding
4. **Parse**: Send to backend AI model for structured extraction
5. **Store**: Create recipe record in database

This approach ensures maximum accuracy by leveraging the same AI model used for image-based recipe imports.