#!/usr/bin/env python3
"""
PDF Recipe Parser - Parse and segment PDF cookbook recipes

This module provides utilities for:
- Segmenting PDF cookbook text into individual recipes
- Parsing recipes with flexible terminology handling
- Converting measurements to modern equivalents when needed
- Handling various recipe formatting patterns
"""

import re
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

# Import the existing recipe parser
try:
    from app.services.recipe_parser import RecipeParser
    from cookbook_db_utils.imports import create_app
except ImportError:
    # For standalone testing
    RecipeParser = None
    create_app = None


class PDFRecipeParser:
    """Parse PDF cookbook recipes with flexible handling"""

    def __init__(self, app_context=None, enable_historical_conversions=True):
        """Initialize PDF recipe parser"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.app_context = app_context
        self.enable_historical_conversions = enable_historical_conversions

        # Historical measurement conversions (optional)
        self.historical_measurements = {
            # Volume measurements
            'gill': '1/4 cup',
            'gills': '1/4 cup each',
            'pint': '2 cups',
            'pints': '2 cups each',
            'quart': '4 cups',
            'quarts': '4 cups each',
            'gallon': '16 cups',
            'gallons': '16 cups each',
            'wine glass': '1/4 cup',
            'wine-glass': '1/4 cup',
            'tumbler': '1 cup',
            'teacup': '3/4 cup',
            'coffee cup': '1 cup',
            'breakfast cup': '1 cup',

            # Weight measurements
            'pound': '16 oz',
            'pounds': '16 oz each',
            'ounce': '1 oz',
            'ounces': '1 oz each',

            # Spoon measurements (standardized later)
            'saltspoon': '1/4 teaspoon',
            'saltspoons': '1/4 teaspoon each',
            'dessertspoon': '2 teaspoons',
            'dessertspoons': '2 teaspoons each',
        }

        # Historical ingredient names to modern equivalents (optional)
        self.ingredient_modernization = {
            'saleratus': 'baking soda',
            'soda': 'baking soda',
            'cream of tartar': 'cream of tartar',
            'pearl ash': 'potash (baking soda substitute)',
            'baker\'s ammonia': 'ammonium carbonate',
            'sour milk': 'buttermilk',
            'sweet milk': 'whole milk',
            'graham flour': 'whole wheat flour',
            'indian meal': 'cornmeal',
            'molasses': 'molasses',
            'treacle': 'molasses',
            'suet': 'beef fat',
            'lard': 'lard',
            'butter': 'butter',
            'eggs': 'eggs',
            'egg': 'egg',
        }

    def segment_cookbook_text(self, full_text: str) -> List[Dict]:
        """
        Segment cookbook text into individual recipes using pattern recognition.

        Args:
            full_text: Complete text from the PDF cookbook

        Returns:
            List of recipe segments with metadata
        """
        self.logger.info("Starting recipe segmentation for PDF cookbook")

        # Clean the text first
        cleaned_text = self._clean_pdf_text(full_text)

        # Split into lines for analysis
        lines = cleaned_text.split('\n')

        recipes = []
        current_recipe = {
            'title': None,
            'content_lines': [],
            'start_line': 0,
            'confidence': 0.0
        }

        for line_num, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines
            if not line:
                if current_recipe['content_lines']:
                    current_recipe['content_lines'].append('')
                continue

            # Check if this line is a recipe title
            title_confidence = self._assess_title_likelihood(line, line_num, lines)

            if title_confidence > 0.7 and current_recipe['title']:
                # This looks like a new recipe title, save the previous one
                if current_recipe['title'] and current_recipe['content_lines']:
                    current_recipe['content'] = '\n'.join(current_recipe['content_lines']).strip()
                    current_recipe['end_line'] = line_num - 1
                    current_recipe['line_count'] = current_recipe['end_line'] - current_recipe['start_line']

                    # Final validation
                    if self._validate_recipe_segment(current_recipe):
                        recipes.append(current_recipe)

                # Start new recipe
                current_recipe = {
                    'title': line,
                    'content_lines': [],
                    'start_line': line_num,
                    'confidence': title_confidence
                }

            elif title_confidence > 0.7 and not current_recipe['title']:
                # First recipe title
                current_recipe['title'] = line
                current_recipe['start_line'] = line_num
                current_recipe['confidence'] = title_confidence

            else:
                # Regular content line
                if current_recipe['title']:  # Only add content if we have a title
                    current_recipe['content_lines'].append(line)

        # Don't forget the last recipe
        if current_recipe['title'] and current_recipe['content_lines']:
            current_recipe['content'] = '\n'.join(current_recipe['content_lines']).strip()
            current_recipe['end_line'] = len(lines)
            current_recipe['line_count'] = current_recipe['end_line'] - current_recipe['start_line']

            if self._validate_recipe_segment(current_recipe):
                recipes.append(current_recipe)

        self.logger.info(f"Segmented text into {len(recipes)} recipe candidates")

        # Post-process and enhance recipes
        enhanced_recipes = []
        for recipe in recipes:
            enhanced = self._enhance_recipe_segment(recipe)
            enhanced_recipes.append(enhanced)

        return enhanced_recipes

    def _clean_pdf_text(self, text: str) -> str:
        """Clean PDF text for better parsing"""
        if not text:
            return ""

        # Normalize whitespace but preserve line breaks
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple blank lines -> double line break

        # Fix common PDF typography issues
        text = text.replace('—', '--')  # Em dash to double dash
        text = text.replace('\u2019', "'")   # Smart single quote to regular
        text = text.replace('\u201c', '"')   # Smart left double quote to regular
        text = text.replace('\u201d', '"')   # Smart right double quote to regular

        # Fix common OCR errors in PDF texts
        text = re.sub(r'\bteaspoonful\b', 'teaspoon', text, flags=re.IGNORECASE)
        text = re.sub(r'\btablespoonful\b', 'tablespoon', text, flags=re.IGNORECASE)
        text = re.sub(r'\bcupful\b', 'cup', text, flags=re.IGNORECASE)

        return text.strip()

    def _assess_title_likelihood(self, line: str, line_num: int, all_lines: List[str]) -> float:
        """
        Assess how likely a line is to be a recipe title.

        Returns confidence score from 0.0 to 1.0
        """
        if not line or len(line) < 3:
            return 0.0

        confidence = 0.0

        # Check formatting patterns
        if line.isupper():
            confidence += 0.4  # Historical cookbooks often used all caps for titles
        elif line.istitle():
            confidence += 0.3  # Title case is also common
        elif line[0].isupper():
            confidence += 0.2  # At least starts with capital

        # Check for food-related words
        food_words = [
            'cake', 'bread', 'soup', 'stew', 'pie', 'pudding', 'sauce', 'salad',
            'chicken', 'beef', 'pork', 'fish', 'eggs', 'beans', 'rice', 'potato',
            'cookies', 'biscuits', 'muffins', 'pancakes', 'waffles', 'custard',
            'jelly', 'preserves', 'pickles', 'roast', 'baked', 'fried', 'boiled',
            'cream', 'butter', 'cheese', 'milk', 'flour', 'sugar', 'tea', 'coffee',
            'apple', 'cherry', 'peach', 'strawberry', 'orange', 'lemon',
            'chops', 'steaks', 'cutlets', 'hash', 'omelet', 'fritters'
        ]

        line_lower = line.lower()
        food_word_count = sum(1 for word in food_words if word in line_lower)
        if food_word_count > 0:
            confidence += min(0.3, food_word_count * 0.1)

        # Check length (titles should be reasonable length)
        if 10 <= len(line) <= 60:
            confidence += 0.2
        elif len(line) > 80:
            confidence -= 0.3  # Too long to be a title

        # Check context (empty line before often indicates new section)
        if line_num > 0 and all_lines[line_num - 1].strip() == "":
            confidence += 0.2

        # Avoid instruction-like lines
        instruction_patterns = [
            r'^\s*(take|add|mix|stir|cook|bake|boil|fry|put|place|heat|serve)',
            r'^\s*\d+\.?\s',  # Numbered steps
            r'\bminutes?\b|\bhours?\b|\bdegrees?\b'  # Time/temperature indicators
        ]

        for pattern in instruction_patterns:
            if re.search(pattern, line_lower):
                confidence -= 0.2

        # Penalize very common words that appear in instructions
        common_instruction_words = ['the', 'and', 'with', 'then', 'until', 'when', 'very']
        common_word_ratio = sum(1 for word in common_instruction_words if word in line_lower.split()) / len(line.split())
        if common_word_ratio > 0.5:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _validate_recipe_segment(self, recipe: Dict) -> bool:
        """Validate that a recipe segment contains reasonable content"""
        if not recipe.get('title') or not recipe.get('content_lines'):
            return False

        content = '\n'.join(recipe['content_lines']).lower()

        # Must have some reasonable length
        if len(content.strip()) < 50:
            return False

        # Enhanced recipe detection for modern cookbooks
        recipe_confidence = self._calculate_recipe_confidence(recipe.get('title', ''), content)
        
        # Use higher threshold for better filtering
        return recipe_confidence > 0.6

    def _calculate_recipe_confidence(self, title: str, content: str) -> float:
        """Calculate confidence that this is actually a recipe page"""
        confidence = 0.0
        
        # Check for non-recipe content patterns
        non_recipe_indicators = [
            'table of contents', 'contents', 'index', 'glossary',
            'introduction', 'preface', 'foreword', 'acknowledgments',
            'bibliography', 'about the author', 'biography',
            'copyright', 'publisher', 'isbn', 'library of congress',
            'nutritional information', 'dietary guidelines',
            'chapter', 'part one', 'part two', 'section',
            'photo credits', 'image credits', 'photography',
            'advertisement', 'sponsors', 'endorsement'
        ]
        
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Strong negative indicators
        for indicator in non_recipe_indicators:
            if indicator in title_lower or indicator in content_lower:
                confidence -= 0.5
                
        # Check for recipe-specific elements
        
        # 1. Ingredient measurements (strong positive indicator)
        measurement_patterns = [
            r'\b\d+(?:\s*\/\s*\d+)?\s*(?:cups?|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|lbs?|pounds?|pints?|quarts?|gallons?)\b',
            r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:cups?|tablespoons?|teaspoons?)\b',
            r'\b\d+\s*(?:degrees?|°)\s*(?:f|fahrenheit|c|celsius)?\b'
        ]
        
        measurement_count = 0
        for pattern in measurement_patterns:
            measurement_count += len(re.findall(pattern, content_lower))
        
        if measurement_count >= 3:
            confidence += 0.4
        elif measurement_count >= 1:
            confidence += 0.2
            
        # 2. Cooking action words (moderate positive indicator)
        cooking_actions = [
            'bake', 'cook', 'boil', 'fry', 'sauté', 'steam', 'roast', 'grill',
            'mix', 'stir', 'whisk', 'beat', 'fold', 'chop', 'dice', 'slice',
            'add', 'combine', 'blend', 'pour', 'sprinkle', 'season',
            'preheat', 'serve', 'garnish', 'cool', 'chill', 'refrigerate'
        ]
        
        action_count = sum(1 for action in cooking_actions if action in content_lower)
        if action_count >= 5:
            confidence += 0.3
        elif action_count >= 2:
            confidence += 0.1
            
        # 3. Common ingredients (moderate positive indicator)
        common_ingredients = [
            'flour', 'sugar', 'salt', 'pepper', 'butter', 'oil', 'eggs?', 'milk',
            'water', 'onion', 'garlic', 'tomato', 'cheese', 'cream', 'vanilla',
            'chicken', 'beef', 'pork', 'fish', 'rice', 'pasta', 'bread'
        ]
        
        ingredient_count = sum(1 for ingredient in common_ingredients 
                             if re.search(r'\b' + ingredient + r'\b', content_lower))
        if ingredient_count >= 5:
            confidence += 0.2
        elif ingredient_count >= 2:
            confidence += 0.1
            
        # 4. Time and temperature references (moderate positive indicator)
        time_temp_patterns = [
            r'\b\d+\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?)\b',
            r'\b\d+\s*(?:degrees?|°)\b',
            r'\boven\b', r'\bstove\b', r'\bmicrowave\b'
        ]
        
        time_temp_count = 0
        for pattern in time_temp_patterns:
            time_temp_count += len(re.findall(pattern, content_lower))
            
        if time_temp_count >= 2:
            confidence += 0.2
        elif time_temp_count >= 1:
            confidence += 0.1
            
        # 5. Recipe structure indicators
        structure_indicators = [
            'ingredients:', 'directions:', 'instructions:', 'method:',
            'preparation:', 'serves', 'servings', 'yield', 'makes'
        ]
        
        structure_count = sum(1 for indicator in structure_indicators 
                            if indicator in content_lower)
        if structure_count >= 2:
            confidence += 0.2
        elif structure_count >= 1:
            confidence += 0.1
            
        # 6. Check content length and structure
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # Recipes should have reasonable length
        if len(non_empty_lines) < 5:
            confidence -= 0.2
        elif len(non_empty_lines) > 50:
            confidence -= 0.1  # Might be a chapter or long article
            
        # 7. Title analysis
        food_words = [
            'cake', 'bread', 'soup', 'stew', 'pie', 'pudding', 'sauce', 'salad',
            'chicken', 'beef', 'pork', 'fish', 'pasta', 'rice', 'pizza',
            'cookies', 'muffins', 'pancakes', 'waffles', 'omelet', 'sandwich'
        ]
        
        title_food_count = sum(1 for word in food_words if word in title_lower)
        if title_food_count >= 1:
            confidence += 0.2
            
        # 8. Penalize purely descriptive or narrative content
        narrative_indicators = [
            'story', 'memory', 'remember', 'family', 'tradition',
            'grew up', 'childhood', 'grandmother', 'mother',
            'first time', 'learned', 'taught me'
        ]
        
        narrative_count = sum(1 for indicator in narrative_indicators 
                            if indicator in content_lower)
        if narrative_count >= 3:
            confidence -= 0.2
            
        return max(0.0, min(1.0, confidence))

    def _enhance_recipe_segment(self, recipe: Dict) -> Dict:
        """Enhance recipe segment with additional metadata and processing"""
        enhanced = recipe.copy()

        # Analyze content to estimate difficulty and other metadata
        content = recipe.get('content', '').lower()

        # Estimate difficulty based on complexity indicators
        complexity_indicators = {
            'easy': ['simple', 'quick', 'easy', 'basic'],
            'medium': ['careful', 'slowly', 'gradually', 'temperature'],
            'hard': ['difficult', 'complex', 'advanced', 'precise', 'delicate']
        }

        difficulty_score = {'easy': 0, 'medium': 0, 'hard': 0}
        for level, indicators in complexity_indicators.items():
            difficulty_score[level] = sum(1 for word in indicators if word in content)

        enhanced['estimated_difficulty'] = max(difficulty_score, key=difficulty_score.get)

        # Try to extract timing information
        time_patterns = [
            r'(\d+)\s*(?:minutes?|mins?)',
            r'(\d+)\s*(?:hours?|hrs?)',
            r'(\d+)\s*(?:seconds?|secs?)'
        ]

        times_found = []
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            times_found.extend([int(m) for m in matches])

        if times_found:
            enhanced['estimated_cook_time'] = max(times_found)  # Take the longest time mentioned

        # Extract serving size hints
        serving_patterns = [
            r'serves?\s*(\d+)',
            r'for\s*(\d+)\s*persons?',
            r'(\d+)\s*people',
            r'(\d+)\s*portions?'
        ]

        for pattern in serving_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                enhanced['estimated_servings'] = int(match.group(1))
                break

        return enhanced

    def parse_pdf_recipe(self, recipe_segment: Dict) -> Dict:
        """
        Parse a PDF recipe segment into structured data.

        Uses the existing RecipeParser with preprocessing for various formats.
        """
        if not RecipeParser or not create_app:
            self.logger.error("RecipeParser not available - cannot parse recipe")
            return self._fallback_parse(recipe_segment)

        # Preprocess the recipe text for historical patterns
        preprocessed_text = self._preprocess_for_modern_parser(recipe_segment)

        try:
            # Create app context if not provided
            if self.app_context:
                app = self.app_context
            else:
                app = create_app('development')

            with app.app_context():
                parser = RecipeParser()

                # Log LLM call for recipe parsing
                recipe_title = recipe_segment.get('title', 'Unknown')[:50]
                self.logger.info(f"🤖 Calling LLM to parse PDF recipe: '{recipe_title}...'")

                # Use the existing parser with our preprocessed text
                parsed_recipe = parser.parse_recipe_text(preprocessed_text, use_cache=False)
                
                # Log successful LLM parsing
                self.logger.info(f"✅ LLM successfully parsed PDF recipe: '{recipe_title}...'")

                # Enhance with cookbook metadata
                parsed_recipe.update({
                    'cookbook_metadata': {
                        'original_title': recipe_segment.get('title', ''),
                        'estimated_difficulty': recipe_segment.get('estimated_difficulty'),
                        'estimated_cook_time': recipe_segment.get('estimated_cook_time'),
                        'estimated_servings': recipe_segment.get('estimated_servings'),
                        'line_count': recipe_segment.get('line_count', 0),
                        'confidence': recipe_segment.get('confidence', 0.0),
                        'source_type': 'pdf_cookbook'
                    }
                })

                return parsed_recipe

        except Exception as e:
            recipe_title = recipe_segment.get('title', 'Unknown')[:50]
            self.logger.warning(f"❌ LLM parsing failed for recipe '{recipe_title}...': {e}")
            self.logger.info(f"🔄 Falling back to manual parsing for recipe '{recipe_title}...'")
            return self._fallback_parse(recipe_segment)

    def _preprocess_for_modern_parser(self, recipe_segment: Dict) -> str:
        """Preprocess PDF recipe text for modern parser compatibility"""
        title = recipe_segment.get('title', '')
        content = recipe_segment.get('content', '')

        # Combine title and content
        full_text = f"{title}\n\n{content}"

        # Convert historical measurements if enabled
        if self.enable_historical_conversions:
            for old_measure, new_measure in self.historical_measurements.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(old_measure) + r'\b'
                full_text = re.sub(pattern, new_measure, full_text, flags=re.IGNORECASE)

            # Modernize ingredient names
            for old_ingredient, new_ingredient in self.ingredient_modernization.items():
                pattern = r'\b' + re.escape(old_ingredient) + r'\b'
                full_text = re.sub(pattern, new_ingredient, full_text, flags=re.IGNORECASE)

        # Add context for better parsing
        context_note = "This is a recipe from a PDF cookbook. Please parse the ingredients and instructions accurately, preserving the original cooking methods and measurements."

        return f"{context_note}\n\n{full_text}"

    def _fallback_parse(self, recipe_segment: Dict) -> Dict:
        """Fallback parsing when modern parser is not available"""
        title = recipe_segment.get('title', 'Untitled Recipe')
        self.logger.info(f"🔧 Using manual fallback parsing for recipe: '{title[:50]}...'")

        content = recipe_segment.get('content', '')

        # Simple extraction of ingredients and instructions
        lines = content.split('\n')
        ingredients = []
        instructions = []

        # Very basic pattern recognition
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line looks like an ingredient (contains measurements)
            measurement_pattern = r'\b(\d+/?\d*)\s*(cups?|tablespoons?|teaspoons?|pounds?|ounces?|pints?|quarts?|gills?)\b'
            if re.search(measurement_pattern, line, re.IGNORECASE):
                ingredients.append(line)
            else:
                instructions.append(line)

        return {
            'title': title,
            'description': f"Recipe from PDF cookbook",
            'ingredients': ingredients,
            'instructions': instructions,
            'prep_time': recipe_segment.get('estimated_cook_time'),
            'servings': recipe_segment.get('estimated_servings'),
            'difficulty': recipe_segment.get('estimated_difficulty', 'medium'),
            'tags': ['pdf_cookbook'],
            'cookbook_metadata': {
                'original_title': title,
                'source_type': 'pdf_cookbook',
                'fallback_parsed': True
            }
        }


# Convenience functions
def process_pdf_cookbook(pdf_path: str, app_context=None, enable_historical_conversions=True) -> List[Dict]:
    """
    Complete pipeline to process a PDF cookbook into parsed recipes.

    Args:
        pdf_path: Path to the PDF file
        app_context: Flask app context (optional)
        enable_historical_conversions: Whether to apply historical measurement conversions

    Returns:
        List of parsed recipe dictionaries
    """
    from cookbook_db_utils.pdf_processor import extract_pdf_cookbook_text

    # Extract text from PDF
    pdf_result = extract_pdf_cookbook_text(pdf_path)

    # Parse recipes
    parser = PDFRecipeParser(app_context, enable_historical_conversions=enable_historical_conversions)
    recipe_segments = parser.segment_cookbook_text(pdf_result['pdf_data']['full_text'])

    # Parse each recipe
    parsed_recipes = []
    for segment in recipe_segments:
        try:
            parsed_recipe = parser.parse_pdf_recipe(segment)
            parsed_recipes.append(parsed_recipe)
        except Exception as e:
            logging.error(f"Failed to parse recipe '{segment.get('title', 'Unknown')}': {e}")

    return parsed_recipes


# Backward compatibility
def process_historical_cookbook_pdf(pdf_path: str, app_context=None) -> List[Dict]:
    """
    Backward compatibility wrapper for historical cookbook processing.
    """
    return process_pdf_cookbook(pdf_path, app_context, enable_historical_conversions=True)


if __name__ == "__main__":
    # Test the historical recipe parser
    import logging

    logging.basicConfig(level=logging.INFO)

    # Test with sample historical text
    sample_text = """
APPLE CUSTARD PIE

Take six large apples, pare and core them, stew them tender, then mash them fine.
Add the yolks of four eggs, half a cup of sugar, one gill of cream,
a little nutmeg and cinnamon. Beat all together, put in a pie plate lined with paste,
and bake half an hour in a moderate oven.

BEEF STEAK PIE

Take two pounds of beef steak, cut in small pieces and season with salt and pepper.
Put in a deep dish with a little water, cover with a good paste,
and bake one hour in a hot oven.
"""

    parser = PDFRecipeParser()
    recipes = parser.segment_cookbook_text(sample_text)

    print(f"Found {len(recipes)} recipes:")
    for i, recipe in enumerate(recipes, 1):
        print(f"{i}. {recipe['title']} (confidence: {recipe['confidence']:.2f})")
        print(f"   Difficulty: {recipe.get('estimated_difficulty', 'unknown')}")
        print(f"   Content length: {len(recipe['content'])} chars")
        print()