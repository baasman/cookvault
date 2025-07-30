#!/usr/bin/env python3
"""
Google Books Metadata Extractor - Fetch cookbook metadata from Google Books API

This module provides utilities for:
- Searching Google Books API by title, author, ISBN
- Extracting comprehensive book metadata
- Handling cookbook-specific searches and validation
- Providing fallback strategies when API searches fail
"""

import re
import logging  
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class GoogleBooksMetadataExtractor:
    """Extract cookbook metadata using Google Books API"""
    
    def __init__(self):
        """Initialize the Google Books metadata extractor"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.base_url = "https://www.googleapis.com/books/v1/volumes"
        self.timeout = 10  # seconds
        
    def extract_metadata_from_pdf_info(self, pdf_path: str, pdf_metadata: Dict = None) -> Dict:
        """
        Extract cookbook metadata from PDF path and content, then enhance with Google Books API.
        
        Args:
            pdf_path: Path to the PDF file
            pdf_metadata: Optional PDF metadata from file
            
        Returns:
            Dictionary with comprehensive cookbook metadata
        """
        pdf_path_obj = Path(pdf_path)
        
        # Extract basic info from filename and PDF metadata
        title_candidates, author_candidates = self._extract_info_from_filename(pdf_path_obj.name)
        
        # Enhance with PDF metadata if available
        if pdf_metadata:
            if pdf_metadata.get('title'):
                title_candidates.insert(0, pdf_metadata['title'])
            if pdf_metadata.get('author'):
                author_candidates.insert(0, pdf_metadata['author'])
        
        # Search Google Books with various strategies
        book_info = self._search_google_books_multiple_strategies(title_candidates, author_candidates)
        
        if book_info:
            self.logger.info(f"📚 Found Google Books match: '{book_info['title']}' by {book_info['authors']}")
            return book_info
        else:
            self.logger.warning("📚 No Google Books match found, using extracted info")
            return self._create_fallback_metadata(title_candidates, author_candidates, pdf_path_obj)
            
    def _extract_info_from_filename(self, filename: str) -> Tuple[List[str], List[str]]:
        """Extract potential title and author information from PDF filename"""
        # Remove file extension
        name = Path(filename).stem
        
        # Common patterns for cookbook filenames
        title_candidates = []
        author_candidates = []
        
        # Clean up the filename
        cleaned_name = self._clean_filename(name)
        
        # Pattern 1: "Author - Title" or "Author_Title"
        if ' - ' in cleaned_name:
            parts = cleaned_name.split(' - ', 1)
            if len(parts) == 2:
                author_candidates.append(parts[0].strip())
                title_candidates.append(parts[1].strip())
        
        # Pattern 2: "Title by Author"
        by_match = re.search(r'(.+?)\s+by\s+(.+?)(?:\s*\(\d+\))?$', cleaned_name, re.IGNORECASE)
        if by_match:
            title_candidates.append(by_match.group(1).strip())
            author_candidates.append(by_match.group(2).strip())
        
        # Pattern 3: Year patterns - remove years from titles
        year_pattern = r'\b(19|20)\d{2}\b'
        cleaned_for_title = re.sub(year_pattern, '', cleaned_name).strip()
        if cleaned_for_title and cleaned_for_title != cleaned_name:
            title_candidates.append(cleaned_for_title)
        
        # Pattern 4: Just use the whole filename as title (fallback)
        title_candidates.append(cleaned_name)
        
        # Remove duplicates while preserving order
        title_candidates = list(dict.fromkeys(title_candidates))
        author_candidates = list(dict.fromkeys(author_candidates))
        
        self.logger.debug(f"Extracted from filename - Titles: {title_candidates}, Authors: {author_candidates}")
        
        return title_candidates, author_candidates
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for better parsing"""
        # Replace underscores and hyphens with spaces
        cleaned = filename.replace('_', ' ').replace('-', ' ')
        
        # Remove common file artifacts
        artifacts = ['pdf', 'ebook', 'cookbook', 'recipes', 'book']
        for artifact in artifacts:
            cleaned = re.sub(rf'\b{artifact}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove edition info like "2nd edition", "revised", etc.
        edition_pattern = r'\b(?:\d+(?:st|nd|rd|th)\s+)?(?:edition|revised|updated|expanded)\b'
        cleaned = re.sub(edition_pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _search_google_books_multiple_strategies(self, titles: List[str], authors: List[str]) -> Optional[Dict]:
        """Search Google Books using multiple strategies to find the best match"""
        
        # Strategy 1: Search with title and author together
        for title in titles[:3]:  # Try first 3 title candidates
            for author in authors[:2]:  # Try first 2 author candidates
                if title and author:
                    result = self._search_google_books(f'intitle:"{title}" inauthor:"{author}"')
                    if result:
                        return result
        
        # Strategy 2: Search with just title (cookbooks often have distinctive titles)
        for title in titles[:3]:
            if title and len(title) > 5:  # Only search meaningful titles
                result = self._search_google_books(f'intitle:"{title}" subject:cooking')
                if result:
                    return result
        
        # Strategy 3: General search with title and cooking filter
        for title in titles[:2]:
            if title:
                result = self._search_google_books(f'"{title}" subject:cooking OR subject:cookbook')
                if result:
                    return result
        
        # Strategy 4: Search with author and cooking filter
        for author in authors[:2]:
            if author and len(author) > 3:
                result = self._search_google_books(f'inauthor:"{author}" subject:cooking')
                if result:
                    return result
        
        return None
    
    def _search_google_books(self, query: str) -> Optional[Dict]:
        """Search Google Books API with a specific query"""
        try:
            self.logger.debug(f"🔍 Searching Google Books: {query}")
            
            params = {
                'q': query,
                'maxResults': 5,  # Get a few results to choose the best one
                'orderBy': 'relevance'
            }
            
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('totalItems', 0) > 0:
                # Find the best match from results
                best_match = self._select_best_match(data['items'], query)
                if best_match:
                    return self._extract_book_info(best_match)
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Google Books API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Error searching Google Books: {e}")
        
        return None
    
    def _select_best_match(self, items: List[Dict], original_query: str) -> Optional[Dict]:
        """Select the best matching book from Google Books results"""
        cookbook_indicators = [
            'cookbook', 'cooking', 'recipes', 'culinary', 'kitchen', 'chef', 
            'baking', 'food', 'cuisine', 'meals', 'dishes'
        ]
        
        scored_items = []
        
        for item in items:
            volume_info = item.get('volumeInfo', {})
            title = volume_info.get('title', '').lower()
            description = volume_info.get('description', '').lower()
            categories = volume_info.get('categories', [])
            
            score = 0
            
            # Score based on cookbook indicators in title
            for indicator in cookbook_indicators:
                if indicator in title:
                    score += 3
                if indicator in description:
                    score += 1
            
            # Score based on categories
            for category in categories:
                category_lower = category.lower()
                if any(word in category_lower for word in ['cooking', 'food', 'cookbook']):
                    score += 5
            
            # Prefer books with more complete metadata
            if volume_info.get('authors'):
                score += 2
            if volume_info.get('publishedDate'):
                score += 1
            if volume_info.get('publisher'):
                score += 1
            
            scored_items.append((score, item))
        
        # Sort by score and return the best match
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        if scored_items and scored_items[0][0] > 0:
            return scored_items[0][1]
        
        # If no cookbook-specific match, return the first result
        return items[0] if items else None
    
    def _extract_book_info(self, book_item: Dict) -> Dict:
        """Extract relevant information from a Google Books API result"""
        volume_info = book_item.get('volumeInfo', {})
        
        # Parse publication date
        pub_date = None
        pub_date_str = volume_info.get('publishedDate', '')
        if pub_date_str:
            try:
                # Handle various date formats
                if len(pub_date_str) == 4:  # Just year
                    pub_date = datetime(int(pub_date_str), 1, 1)
                elif len(pub_date_str) == 7:  # YYYY-MM
                    year, month = pub_date_str.split('-')
                    pub_date = datetime(int(year), int(month), 1)
                else:  # Full date
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.logger.debug(f"Could not parse publication date: {pub_date_str}")
        
        # Extract authors
        authors = volume_info.get('authors', [])
        author_str = ', '.join(authors) if authors else 'Unknown'
        
        # Extract categories/subjects for additional tags
        categories = volume_info.get('categories', [])
        
        return {
            'title': volume_info.get('title', 'Unknown Cookbook'),
            'author': author_str,
            'authors': authors,
            'description': volume_info.get('description', ''),
            'publisher': volume_info.get('publisher', ''),
            'publication_date': pub_date,
            'isbn_10': self._extract_isbn(volume_info, 'ISBN_10'),
            'isbn_13': self._extract_isbn(volume_info, 'ISBN_13'),
            'page_count': volume_info.get('pageCount'),
            'categories': categories,
            'language': volume_info.get('language', 'en'),
            'google_books_id': book_item.get('id'),
            'thumbnail_url': volume_info.get('imageLinks', {}).get('thumbnail'),
            'preview_url': volume_info.get('previewLink'),
            'info_url': volume_info.get('infoLink'),
            'source': 'google_books'
        }
    
    def _extract_isbn(self, volume_info: Dict, isbn_type: str) -> Optional[str]:
        """Extract ISBN from volume info"""
        identifiers = volume_info.get('industryIdentifiers', [])
        for identifier in identifiers:
            if identifier.get('type') == isbn_type:
                return identifier.get('identifier')
        return None
    
    def _create_fallback_metadata(self, titles: List[str], authors: List[str], pdf_path: Path) -> Dict:
        """Create fallback metadata when Google Books search fails"""
        title = titles[0] if titles else pdf_path.stem.replace('_', ' ').title()
        author = authors[0] if authors else 'Unknown'
        
        return {
            'title': title,
            'author': author,
            'authors': [author] if author != 'Unknown' else [],
            'description': f'Cookbook imported from PDF file: {pdf_path.name}',
            'publisher': '',
            'publication_date': None,
            'isbn_10': None,
            'isbn_13': None,
            'page_count': None,
            'categories': ['Cooking'],
            'language': 'en',
            'google_books_id': None,
            'thumbnail_url': None,
            'preview_url': None,
            'info_url': None,
            'source': 'extracted_from_filename'
        }

    def search_by_isbn(self, isbn: str) -> Optional[Dict]:
        """Search Google Books by ISBN"""
        if not isbn:
            return None
            
        # Clean ISBN (remove hyphens, spaces)
        clean_isbn = re.sub(r'[^\d]', '', isbn)
        
        if len(clean_isbn) not in [10, 13]:
            self.logger.warning(f"Invalid ISBN length: {clean_isbn}")
            return None
        
        return self._search_google_books(f'isbn:{clean_isbn}')
    
    def search_by_title_author(self, title: str, author: str = None) -> Optional[Dict]:
        """Search Google Books by title and optionally author"""
        if not title:
            return None
            
        if author:
            query = f'intitle:"{title}" inauthor:"{author}"'
        else:
            query = f'intitle:"{title}" subject:cooking'
            
        return self._search_google_books(query)


# Convenience function for direct usage
def get_cookbook_metadata(pdf_path: str, pdf_metadata: Dict = None) -> Dict:
    """
    Get cookbook metadata from PDF path using Google Books API.
    
    Args:
        pdf_path: Path to the PDF file
        pdf_metadata: Optional PDF metadata from file
        
    Returns:
        Dictionary with cookbook metadata
    """
    extractor = GoogleBooksMetadataExtractor()
    return extractor.extract_metadata_from_pdf_info(pdf_path, pdf_metadata)


if __name__ == "__main__":
    # Test the Google Books metadata extractor
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # Test with a sample cookbook filename
    test_files = [
        "Julia_Child_Mastering_the_Art_of_French_Cooking_1961.pdf",
        "The Joy of Cooking by Irma Rombauer.pdf",
        "betty_crocker_cookbook_2020_edition.pdf",
        "175_choice_recipes_chicago_womens_club_1887.pdf"
    ]
    
    extractor = GoogleBooksMetadataExtractor()
    
    for test_file in test_files:
        print(f"\n🧪 Testing: {test_file}")
        print("=" * 60)
        
        try:
            metadata = extractor.extract_metadata_from_pdf_info(test_file)
            print(f"📚 Title: {metadata['title']}")
            print(f"✍️  Author: {metadata['author']}")
            print(f"🏢 Publisher: {metadata['publisher']}")
            print(f"📅 Published: {metadata['publication_date']}")
            print(f"🔖 Source: {metadata['source']}")
            
            if metadata.get('description'):
                print(f"📝 Description: {metadata['description'][:100]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")