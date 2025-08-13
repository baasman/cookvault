# Contributing to Cookbook Creator 🤝

Thank you for your interest in contributing to Cookbook Creator! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Architecture Overview](#architecture-overview)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## 📝 Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code:

- **Be respectful** - Treat all contributors and users with respect
- **Be inclusive** - Welcome newcomers and help them learn
- **Be constructive** - Provide helpful feedback and suggestions
- **Be patient** - Remember that everyone has different skill levels
- **Be collaborative** - Work together to improve the project

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.11+ installed
- Node.js 18+ installed
- Git for version control
- A code editor (VS Code recommended)
- Basic understanding of React and Flask

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cookbook-creator.git
   cd cookbook-creator
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/cookbook-creator.git
   ```

### Local Setup

Follow the setup instructions in [README.md](README.md) to get the development environment running.

## 🔄 Development Workflow

### Branching Strategy

- **`main`** - Production-ready code
- **Feature branches** - `feature/description-of-feature`
- **Bug fixes** - `fix/description-of-bug`
- **Documentation** - `docs/description-of-change`

### Development Process

1. **Sync with upstream**:
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** (see [Coding Standards](#coding-standards))

4. **Test your changes**:
   ```bash
   # Backend tests
   cd backend && pytest
   
   # Frontend tests  
   cd frontend && npm test
   
   # Manual testing
   npm run dev  # Frontend
   uv run python run.py  # Backend
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add description of your feature"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** (see [Pull Request Process](#pull-request-process))

## 📏 Coding Standards

### General Guidelines

- **Write clear, readable code** - Code is read more than written
- **Use meaningful names** - Variables, functions, and classes should be self-documenting
- **Keep functions small** - Each function should do one thing well
- **Add comments for complex logic** - Explain the "why", not the "what"
- **Follow existing patterns** - Be consistent with the codebase

### Frontend (React/TypeScript)

#### File Organization
```
src/
├── components/
│   ├── ui/           # Generic UI components
│   ├── recipe/       # Recipe-specific components
│   └── cookbook/     # Cookbook-specific components
├── pages/            # Page-level components
├── services/         # API service layer
├── hooks/            # Custom React hooks
├── utils/            # Utility functions
└── types/            # TypeScript type definitions
```

#### Code Style
```typescript
// ✅ Good - Clear component structure
interface RecipeCardProps {
  recipe: Recipe;
  onEdit?: () => void;
  showActions?: boolean;
}

export const RecipeCard: React.FC<RecipeCardProps> = ({ 
  recipe, 
  onEdit, 
  showActions = false 
}) => {
  const handleEdit = useCallback(() => {
    if (onEdit) {
      onEdit();
    }
  }, [onEdit]);

  return (
    <div className="recipe-card">
      {/* Component JSX */}
    </div>
  );
};
```

#### TypeScript Guidelines
- Always define proper interfaces/types
- Use strict mode (`strict: true` in tsconfig.json)
- Avoid `any` types - use proper typing
- Export types from a central `types/` directory

#### React Best Practices
- Use functional components with hooks
- Implement proper error boundaries
- Use React Query for data fetching
- Memoize expensive calculations with `useMemo`
- Use `useCallback` for event handlers

### Backend (Python/Flask)

#### File Organization
```
app/
├── api/              # API route handlers
├── models/           # Database models
├── services/         # Business logic
├── utils/            # Utility functions
└── __init__.py       # Flask app factory
```

#### Code Style
```python
# ✅ Good - Clear function structure
def create_recipe(user_id: int, recipe_data: Dict[str, Any]) -> Recipe:
    """
    Create a new recipe for the specified user.
    
    Args:
        user_id: ID of the user creating the recipe
        recipe_data: Dictionary containing recipe information
        
    Returns:
        Recipe: The created recipe instance
        
    Raises:
        ValidationError: If recipe data is invalid
    """
    # Validate input data
    if not recipe_data.get('title'):
        raise ValidationError("Recipe title is required")
    
    # Create recipe instance
    recipe = Recipe(
        title=recipe_data['title'],
        description=recipe_data.get('description'),
        user_id=user_id
    )
    
    # Save to database
    db.session.add(recipe)
    db.session.commit()
    
    return recipe
```

#### Python Guidelines
- Follow PEP 8 style guide
- Use type hints for all function parameters and return values
- Write comprehensive docstrings
- Use proper exception handling
- Keep database transactions atomic

### Database

- **Use migrations** for all schema changes
- **Write descriptive migration messages**
- **Test migrations** both up and down
- **Use appropriate indexes** for performance
- **Follow naming conventions**:
  - Tables: `snake_case` (e.g., `recipe_ingredients`)
  - Columns: `snake_case` (e.g., `created_at`)
  - Indexes: `idx_tablename_columnname`

### API Design

- **Use RESTful conventions**
- **Return consistent JSON structures**
- **Include proper HTTP status codes**
- **Validate all input data**
- **Handle errors gracefully**

```python
# ✅ Good - Consistent API response structure
@api.route('/recipes', methods=['GET'])
@jwt_required()
def get_recipes():
    try:
        recipes = Recipe.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'success': True,
            'data': [recipe.to_dict() for recipe in recipes],
            'count': len(recipes)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

## 🔍 Pull Request Process

### Before Creating a PR

1. **Sync your branch** with the latest main
2. **Run all tests** and ensure they pass
3. **Check code style** with linting tools
4. **Update documentation** if needed
5. **Test manually** in development environment

### PR Requirements

Your Pull Request should include:

- **Clear title** describing the change
- **Detailed description** of what was changed and why
- **Screenshots** for UI changes
- **Test coverage** for new features
- **Documentation updates** if applicable
- **Breaking change notes** if any

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Browser testing completed (for UI changes)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No console.log or debug statements left
```

### Review Process

1. **Automated checks** must pass (linting, tests)
2. **Code review** by at least one maintainer
3. **Manual testing** by reviewers if needed
4. **Approval** from maintainers
5. **Merge** using squash and merge strategy

## 🐛 Issue Guidelines

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check the documentation** for solutions
3. **Try the latest version** to see if it's already fixed

### Issue Templates

#### Bug Report
```markdown
## Bug Description
Clear description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- Browser: [e.g., Chrome 91]
- OS: [e.g., macOS 12.0]
- Version: [e.g., 1.2.3]

## Screenshots
If applicable, add screenshots to help explain your problem.
```

#### Feature Request
```markdown
## Feature Description
Clear description of the feature you'd like to see.

## Problem Statement
What problem would this feature solve?

## Proposed Solution
How would you like this feature to work?

## Alternatives Considered
Any alternative solutions or features you've considered.

## Additional Context
Any other context about the feature request.
```

## 🏗️ Architecture Overview

### Frontend Architecture

```
React App
├── React Router (Navigation)
├── React Query (State Management)
├── Context API (Auth State)
└── Tailwind CSS (Styling)
```

### Backend Architecture

```
Flask Application
├── Blueprint-based routing
├── SQLAlchemy ORM
├── JWT Authentication
├── Service Layer Pattern
└── Database Migrations
```

### Key Patterns

- **Component Composition** - Build UIs from small, reusable components
- **Custom Hooks** - Encapsulate stateful logic
- **Service Layer** - Separate business logic from API routes
- **Repository Pattern** - Abstract database access
- **Error Boundaries** - Handle React errors gracefully

## 🧪 Testing Guidelines

### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test RecipeCard.test.tsx
```

#### Test Structure
```typescript
describe('RecipeCard', () => {
  const mockRecipe = {
    id: 1,
    title: 'Test Recipe',
    // ... other properties
  };

  it('renders recipe title correctly', () => {
    render(<RecipeCard recipe={mockRecipe} />);
    expect(screen.getByText('Test Recipe')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const mockOnEdit = jest.fn();
    render(<RecipeCard recipe={mockRecipe} onEdit={mockOnEdit} showActions />);
    
    const editButton = screen.getByRole('button', { name: /edit/i });
    await userEvent.click(editButton);
    
    expect(mockOnEdit).toHaveBeenCalledTimes(1);
  });
});
```

### Backend Testing

```bash
# Run tests
cd backend && pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_recipes.py::TestRecipeAPI::test_create_recipe
```

#### Test Structure
```python
class TestRecipeAPI:
    """Test cases for Recipe API endpoints."""
    
    def test_create_recipe_success(self, client, auth_headers):
        """Test successful recipe creation."""
        recipe_data = {
            'title': 'Test Recipe',
            'description': 'A test recipe',
            'ingredients': ['ingredient1', 'ingredient2'],
            'instructions': ['step1', 'step2']
        }
        
        response = client.post(
            '/api/recipes',
            json=recipe_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == 'Test Recipe'
        assert 'id' in data
```

## 📚 Documentation

### Code Documentation

- **Functions/Methods** - Include docstrings with parameters and return values
- **Classes** - Document purpose and key methods
- **Complex Logic** - Add inline comments explaining the approach
- **API Endpoints** - Document expected inputs and outputs

### README Updates

When making significant changes, update:
- **Feature list** if adding new functionality
- **Setup instructions** if changing requirements
- **API documentation** if modifying endpoints
- **Configuration** if adding new environment variables

### Commit Messages

Use conventional commit format:

```
type(scope): brief description

Detailed explanation if needed

- feat: new feature
- fix: bug fix  
- docs: documentation changes
- style: formatting changes
- refactor: code restructuring
- test: test additions/modifications
- chore: maintenance tasks
```

Examples:
```
feat(auth): add JWT token refresh endpoint
fix(recipe): resolve image upload validation error
docs(api): update recipe endpoint documentation
refactor(database): optimize recipe query performance
```

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

### 🔥 High Priority
- **Testing** - Increase test coverage
- **Performance** - Optimize slow queries and large image handling
- **Accessibility** - Improve keyboard navigation and screen reader support
- **Mobile UI** - Enhance mobile responsiveness

### 📈 Medium Priority
- **Internationalization** - Add multi-language support
- **Advanced Search** - Improve recipe search with filters
- **Social Features** - Recipe ratings and comments
- **Export Features** - PDF generation and recipe sharing

### 💡 Nice to Have
- **PWA Support** - Offline functionality
- **Recipe Scaling** - Automatic ingredient quantity adjustment
- **Meal Planning** - Weekly meal planning features
- **Integration** - Third-party recipe imports

## ❓ Questions?

If you have questions about contributing:

1. **Check existing issues** and discussions
2. **Ask in GitHub Discussions** for general questions
3. **Create an issue** for specific bugs or features
4. **Join our community** Discord/Slack (if available)

## 🙏 Recognition

Contributors will be recognized in:
- **Contributors section** of README.md
- **Release notes** for significant contributions
- **All Contributors** bot recognition
- **Special mentions** in project updates

---

**Thank you for contributing to Cookbook Creator! Your efforts help make cooking and recipe management better for everyone.** 🍳❤️