#!/usr/bin/env python3
"""
Recipe import script for importing LaTeX recipes from GitHub repository.
This script crawls the drewnutt/CookBook repository and imports all .tex recipe files
using the backend's text upload API with AI parsing for maximum accuracy.
"""

import os
import sys
import json
import time
import requests
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass
class RecipeFile:
    """Represents a recipe file in the repository."""
    name: str
    path: str
    category: str
    download_url: str


class GitHubCrawler:
    """Crawls the GitHub repository to find all recipe files."""
    
    def __init__(self, repo_owner: str, repo_name: str, branch: str = "master"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.base_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.raw_base_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        
    def get_repository_structure(self) -> List[Dict]:
        """Get the top-level directory structure of the repository."""
        url = f"{self.base_api_url}/contents"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_directory_contents(self, path: str) -> List[Dict]:
        """Get contents of a specific directory."""
        url = f"{self.base_api_url}/contents/{path}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def find_recipe_directories(self) -> List[str]:
        """Find all directories that likely contain recipes."""
        structure = self.get_repository_structure()
        
        # Known recipe directories from our research
        known_recipe_dirs = {
            "Bread", "Breakfast", "Curries", "Dessert", 
            "Entrees", "Instant_Pot", "Side_Dishes", "Substitutes"
        }
        
        recipe_dirs = []
        for item in structure:
            if item["type"] == "dir" and item["name"] in known_recipe_dirs:
                recipe_dirs.append(item["name"])
                print(f"Found recipe directory: {item['name']}")
        
        return recipe_dirs
    
    def find_recipe_files(self) -> List[RecipeFile]:
        """Find all .tex recipe files in the repository."""
        recipe_dirs = self.find_recipe_directories()
        all_recipe_files = []
        
        for category in recipe_dirs:
            print(f"Scanning {category} directory...")
            try:
                contents = self.get_directory_contents(category)
                
                for item in contents:
                    if item["type"] == "file" and item["name"].endswith(".tex"):
                        recipe_file = RecipeFile(
                            name=item["name"],
                            path=item["path"],
                            category=category,
                            download_url=item["download_url"]
                        )
                        all_recipe_files.append(recipe_file)
                        print(f"  Found recipe: {item['name']}")
                
            except Exception as e:
                print(f"Error scanning {category}: {e}")
        
        print(f"Total recipe files found: {len(all_recipe_files)}")
        return all_recipe_files
    
    def download_recipe_content(self, recipe_file: RecipeFile) -> str:
        """Download the content of a recipe file."""
        response = requests.get(recipe_file.download_url)
        response.raise_for_status()
        return response.text


class LaTeXProcessor:
    """Processes LaTeX recipe files for AI parsing."""
    
    @staticmethod
    def clean_latex_content(latex_content: str) -> str:
        """Clean LaTeX content to make it more suitable for AI parsing."""
        # Remove LaTeX comments
        latex_content = re.sub(r'%.*$', '', latex_content, flags=re.MULTILINE)
        
        # Convert common LaTeX commands to readable text
        replacements = {
            r'\\begin{recipe}': '--- RECIPE START ---',
            r'\\end{recipe}': '--- RECIPE END ---',
            r'\\ingredients': '\nINGREDIENTS:',
            r'\\preparation': '\nPREPARATION:',
            r'\\step': '\nSTEP:',
            r'\\recipetitle{([^}]*)}': r'RECIPE TITLE: \1',
            r'\\preptime{([^}]*)}': r'PREP TIME: \1',
            r'\\baketime{([^}]*)}': r'BAKE TIME: \1',
            r'\\cooktime{([^}]*)}': r'COOK TIME: \1',
            r'\\portions{([^}]*)}': r'SERVES: \1',
            r'\\source{([^}]*)}': r'SOURCE: \1',
            r'\\index{([^}]*)}': r'TAGS: \1',
            r'\\textbf{([^}]*)}': r'\1',
            r'\\emph{([^}]*)}': r'\1',
            r'\\\\': '\n',
        }
        
        for pattern, replacement in replacements.items():
            latex_content = re.sub(pattern, replacement, latex_content, flags=re.IGNORECASE)
        
        # Remove remaining LaTeX commands
        latex_content = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})*', '', latex_content)
        
        # Clean up whitespace
        latex_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', latex_content)
        latex_content = re.sub(r'[ \t]+', ' ', latex_content)
        
        return latex_content.strip()
    
    @staticmethod
    def extract_recipe_metadata(latex_content: str) -> Dict[str, str]:
        """Extract metadata from LaTeX content."""
        metadata = {}
        
        patterns = {
            'title': r'\\recipetitle\{([^}]*)\}',
            'prep_time': r'\\preptime\{([^}]*)\}',
            'bake_time': r'\\baketime\{([^}]*)\}',
            'cook_time': r'\\cooktime\{([^}]*)\}',
            'portions': r'\\portions\{([^}]*)\}',
            'source': r'\\source\{([^}]*)\}',
            'tags': r'\\index\{([^}]*)\}'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, latex_content, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()
        
        return metadata


class RecipeUploader:
    """Handles uploading recipes to the backend API."""
    
    def __init__(self, api_url: str, auth_token: str, max_retries: int = 3, retry_delay: int = 2):
        self.api_url = api_url
        self.auth_token = auth_token
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        })
        # Set reasonable timeouts
        self.session.timeout = (10, 60)  # 10s connection, 60s read
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a request with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Return immediately on success or client error (no point retrying)
                if response.status_code < 500:
                    return response
                
                # Server error - retry
                print(f"  Server error (attempt {attempt + 1}/{self.max_retries}): {response.status_code}")
                
            except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
                last_exception = e
                print(f"  Network error (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        # All retries failed
        if last_exception:
            raise last_exception
        return None
    
    def create_cookbook(self, title: str, author: str = "", description: str = "") -> Optional[int]:
        """Create a new cookbook and return its ID."""
        data = {
            "create_new_cookbook": True,
            "new_cookbook_title": title,
            "new_cookbook_author": author,
            "new_cookbook_description": description,
            "text": "dummy text"  # Required but will be ignored
        }
        
        try:
            response = self._make_request_with_retry(
                "POST",
                urljoin(self.api_url, "/api/recipes/upload-text"),
                json=data
            )
            
            if response and response.status_code == 201:
                result = response.json()
                cookbook = result.get("cookbook")
                if cookbook:
                    return cookbook["id"]
            elif response:
                print(f"Failed to create cookbook: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error creating cookbook: {e}")
        
        return None
    
    def upload_recipe(self, recipe_text: str, cookbook_id: Optional[int] = None, 
                     page_number: Optional[int] = None) -> Tuple[bool, Dict]:
        """Upload a recipe text to the backend."""
        data = {
            "text": recipe_text,
            "cookbook_id": cookbook_id,
            "page_number": page_number
        }
        
        try:
            response = self._make_request_with_retry(
                "POST",
                urljoin(self.api_url, "/api/recipes/upload-text"),
                json=data
            )
            
            if response and response.status_code == 201:
                return True, response.json()
            elif response:
                error_info = {"status_code": response.status_code, "response": response.text}
                return False, error_info
            else:
                return False, {"error": "Request failed after all retries"}
                
        except Exception as e:
            return False, {"error": str(e)}


class RecipeImporter:
    """Main class orchestrating the recipe import process."""
    
    def __init__(self, api_url: str, auth_token: str):
        self.crawler = GitHubCrawler("drewnutt", "CookBook")
        self.processor = LaTeXProcessor()
        self.uploader = RecipeUploader(api_url, auth_token)
        self.stats = {
            "total_found": 0,
            "successful_imports": 0,
            "failed_imports": 0,
            "errors": []
        }
    
    def import_all_recipes(self, cookbook_title: str = "Imported LaTeX Cookbook", 
                          resume_from: int = 0, save_progress: bool = True) -> Dict:
        """Import all recipes from the GitHub repository."""
        print("Starting recipe import process...")
        
        # Find all recipe files
        recipe_files = self.crawler.find_recipe_files()
        self.stats["total_found"] = len(recipe_files)
        
        if not recipe_files:
            print("No recipe files found!")
            return self.stats
        
        # Create cookbook for imported recipes
        print(f"Creating cookbook: {cookbook_title}")
        cookbook_id = self.uploader.create_cookbook(
            title=cookbook_title,
            author="Drew Nutting",
            description="Recipes imported from https://github.com/drewnutt/CookBook LaTeX cookbook collection"
        )
        
        if not cookbook_id:
            print("Failed to create cookbook, importing without cookbook association")
        else:
            print(f"Created cookbook with ID: {cookbook_id}")
        
        # Load progress file if resuming
        progress_file = "import_progress.json"
        processed_files = set()
        
        if resume_from > 0:
            try:
                with open(progress_file, "r") as f:
                    progress_data = json.load(f)
                    processed_files = set(progress_data.get("processed_files", []))
                    self.stats.update(progress_data.get("stats", self.stats))
                print(f"Resuming from recipe {resume_from}, {len(processed_files)} already processed")
            except FileNotFoundError:
                print("No progress file found, starting fresh")
        
        # Process each recipe file
        for i, recipe_file in enumerate(recipe_files, 1):
            # Skip if already processed (for resume functionality)
            if recipe_file.name in processed_files:
                print(f"[{i}/{len(recipe_files)}] Skipping already processed: {recipe_file.name}")
                continue
            
            # Skip if we're resuming and haven't reached the resume point
            if i < resume_from:
                continue
                
            print(f"\n[{i}/{len(recipe_files)}] Processing {recipe_file.category}/{recipe_file.name}")
            
            try:
                # Download recipe content
                latex_content = self.crawler.download_recipe_content(recipe_file)
                
                # Process LaTeX content
                cleaned_text = self.processor.clean_latex_content(latex_content)
                
                # Add category context for better AI parsing
                categorized_text = f"RECIPE CATEGORY: {recipe_file.category}\n\n{cleaned_text}"
                
                # Upload to backend
                success, result = self.uploader.upload_recipe(
                    recipe_text=categorized_text,
                    cookbook_id=cookbook_id,
                    page_number=i
                )
                
                if success:
                    recipe_info = result.get("recipe", {})
                    print(f"  ✅ Successfully imported: {recipe_info.get('title', 'Untitled')}")
                    self.stats["successful_imports"] += 1
                    processed_files.add(recipe_file.name)
                else:
                    error_msg = f"Upload failed: {result}"
                    print(f"  ❌ {error_msg}")
                    self.stats["failed_imports"] += 1
                    self.stats["errors"].append({
                        "file": recipe_file.name,
                        "error": error_msg
                    })
                
                # Save progress periodically
                if save_progress and (self.stats["successful_imports"] + self.stats["failed_imports"]) % 5 == 0:
                    progress_data = {
                        "processed_files": list(processed_files),
                        "stats": self.stats,
                        "last_processed_index": i,
                        "cookbook_id": cookbook_id
                    }
                    with open(progress_file, "w") as f:
                        json.dump(progress_data, f, indent=2)
                    print(f"  💾 Progress saved")
                
                # Add delay to avoid overwhelming the server
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"Processing error: {str(e)}"
                print(f"  ❌ {error_msg}")
                self.stats["failed_imports"] += 1
                self.stats["errors"].append({
                    "file": recipe_file.name,
                    "error": error_msg
                })
        
        return self.stats
    
    def print_summary(self):
        """Print import summary."""
        print("\n" + "="*50)
        print("IMPORT SUMMARY")
        print("="*50)
        print(f"Total recipes found: {self.stats['total_found']}")
        print(f"Successfully imported: {self.stats['successful_imports']}")
        print(f"Failed imports: {self.stats['failed_imports']}")
        
        if self.stats["errors"]:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:  # Show first 10 errors
                print(f"  - {error['file']}: {error['error']}")
            if len(self.stats["errors"]) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more errors")


def main():
    """Main function."""
    # Get configuration from environment or command line
    api_url = os.getenv("API_URL", "http://localhost:5000")
    auth_token = os.getenv("AUTH_TOKEN")
    
    if not auth_token:
        print("Error: AUTH_TOKEN environment variable is required")
        print("Please set your JWT token: export AUTH_TOKEN='your_jwt_token_here'")
        sys.exit(1)
    
    print(f"Using API URL: {api_url}")
    print("Starting import process...\n")
    
    # Create importer and run
    importer = RecipeImporter(api_url, auth_token)
    stats = importer.import_all_recipes()
    importer.print_summary()
    
    # Save detailed results
    with open("import_results.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nDetailed results saved to: import_results.json")


if __name__ == "__main__":
    main()