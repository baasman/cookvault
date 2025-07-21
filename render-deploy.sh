#!/bin/bash

# CookVault Render Deployment Script
# This script helps deploy both backend and frontend to Render

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}  CookVault Render Deployment${NC}"
    echo -e "${BLUE}===========================================${NC}"
}

# Check if render CLI is installed
check_render_cli() {
    if ! command -v render &> /dev/null; then
        print_error "Render CLI is not installed."
        echo "Install it with one of these methods:"
        echo "  Homebrew: brew install render"
        echo "  Script:   curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh"
        echo "  Manual:   https://github.com/render-oss/cli/releases/"
        echo "Documentation: https://render.com/docs/cli"
        exit 1
    fi
    
    print_success "Render CLI is installed"
}

# Check if user is logged in to Render
check_render_auth() {
    if ! render whoami &> /dev/null; then
        print_error "You are not logged in to Render."
        echo "Run: render login"
        exit 1
    fi
    
    print_success "Logged in to Render as: $(render whoami)"
}

# Check if CookVault project exists and show project info
check_render_project() {
    print_status "Checking Render projects..."
    
    # Try to list projects with a timeout
    local projects_output=""
    local timeout_duration=10
    
    # Use timeout command if available, otherwise skip project check
    if command -v timeout &> /dev/null; then
        if projects_output=$(timeout $timeout_duration render projects list 2>/dev/null); then
            if echo "$projects_output" | grep -q "CookVault"; then
                print_success "Found CookVault project"
            else
                print_warning "CookVault project not found in your account"
                echo "Available projects:"
                echo "$projects_output"
                echo ""
                echo "Please ensure you have access to the CookVault project"
                echo "The deployment will attempt to create services anyway..."
            fi
        else
            print_warning "Could not list projects (timeout or command failed)"
            print_status "This is normal for some accounts. Proceeding with deployment..."
        fi
    else
        # On systems without timeout command, skip the project check
        print_warning "Skipping project check (timeout command not available)"
        print_status "Proceeding with deployment..."
    fi
    
    print_status "Note: Services will be created in your default project or CookVault if accessible"
}

# Validate required files exist
validate_files() {
    local required_files=(
        "render.yaml"
        "backend/Dockerfile.render"
        "backend/start.sh"
        "frontend/package.json"
        ".env.production.example"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "Required file missing: $file"
            exit 1
        fi
    done
    
    print_success "All required files are present"
}

# Check environment variables setup
check_env_vars() {
    print_status "Checking environment variables..."
    
    if [[ ! -f ".env.production" ]]; then
        print_warning ".env.production not found"
        echo "Copy .env.production.example to .env.production and fill in your values:"
        echo "  cp .env.production.example .env.production"
        echo ""
        echo "Required variables:"
        echo "  - SECRET_KEY"
        echo "  - DATABASE_URL (your Render PostgreSQL URL)"
        echo "  - REDIS_URL (your Render Redis URL)"
        echo "  - ANTHROPIC_API_KEY"
        echo "  - GOOGLE_BOOKS_API_KEY (optional)"
        echo "  - CORS_ORIGINS"
        echo ""
        print_warning "After setting up .env.production, you'll need to set these as secrets in Render dashboard"
        return 1
    fi
    
    print_success "Environment file exists"
    return 0
}

# Deploy using Render blueprint
deploy_blueprint() {
    print_status "Deploying services using Render blueprint..."
    print_status "This will create services in your CookVault project..."
    
    # Check if blueprint command is available
    if render --help 2>&1 | grep -q "blueprint"; then
        print_status "Using blueprint deployment..."
        if render blueprint launch render.yaml; then
            print_success "Blueprint deployment initiated!"
            print_status "Services are being deployed. Check Render dashboard for progress."
            print_status "The services will be created in your CookVault project."
        else
            print_error "Blueprint deployment failed"
            echo ""
            print_warning "Falling back to manual deployment instructions..."
            deploy_manual
            return 1
        fi
    else
        print_warning "Blueprint command not available in your Render CLI version"
        print_status "Your CLI doesn't support blueprint deployment."
        echo ""
        print_status "Don't worry! Here are your deployment options:"
        echo ""
        echo "Option 1: Update to latest Render CLI (recommended):"
        echo "  brew upgrade render"
        echo "  # Or reinstall: curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh"
        echo ""
        echo "Option 2: Manual deployment via dashboard:"
        echo "  See detailed instructions in: DASHBOARD_DEPLOYMENT.md"
        echo ""
        deploy_manual
        return 1
    fi
}

# Manual deployment option
deploy_manual() {
    print_status "Manual deployment instructions for CookVault project:"
    echo ""
    echo "Go to https://dashboard.render.com and select your CookVault project, then:"
    echo ""
    echo "1. Backend Service:"
    echo "   - Click 'New +' → 'Web Service'"
    echo "   - Connect your GitHub repository"
    echo "   - Name: cookvault-backend"
    echo "   - Runtime: Docker"
    echo "   - Dockerfile Path: backend/Dockerfile.render"
    echo "   - Health Check Path: /api/health"
    echo "   - Plan: Starter (or higher)"
    echo ""
    echo "2. Frontend Service:"
    echo "   - Click 'New +' → 'Static Site'"
    echo "   - Connect your GitHub repository"
    echo "   - Name: cookvault-frontend"
    echo "   - Build Command: cd frontend && npm ci && npm run build"
    echo "   - Publish Directory: frontend/dist"
    echo ""
    echo "3. Environment Variables (set as secrets in backend service):"
    if [[ -f ".env.production.example" ]]; then
        cat .env.production.example | grep -E "^[A-Z]" | grep -v "^#"
    fi
    echo ""
    echo "4. Connect to existing databases:"
    echo "   - Use your existing PostgreSQL DATABASE_URL"
    echo "   - Use your existing Redis REDIS_URL"
    echo ""
}

# Show post-deployment steps
show_post_deployment() {
    print_header
    print_success "Deployment configuration complete!"
    echo ""
    print_status "Next steps:"
    echo "1. Check your Render dashboard for deployment progress"
    echo "2. Set environment variables as secrets in Render dashboard:"
    echo "   - SECRET_KEY"
    echo "   - DATABASE_URL"
    echo "   - REDIS_URL"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_BOOKS_API_KEY"
    echo "   - CORS_ORIGINS"
    echo ""
    echo "3. Once deployed, test your application:"
    echo "   - Backend health check: https://your-backend-url.onrender.com/api/health"
    echo "   - Frontend: https://your-frontend-url.onrender.com"
    echo ""
    echo "4. Monitor logs:"
    echo "   - render logs cookvault-backend"
    echo "   - render logs cookvault-frontend"
    echo ""
    echo "For troubleshooting, see DEPLOYMENT.md"
}

# Main deployment function
main() {
    print_header
    
    # Parse command line arguments
    MANUAL_MODE=false
    SKIP_ENV_CHECK=false
    SKIP_PROJECT_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --manual)
                MANUAL_MODE=true
                shift
                ;;
            --skip-env-check)
                SKIP_ENV_CHECK=true
                shift
                ;;
            --skip-project-check)
                SKIP_PROJECT_CHECK=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --manual              Show manual deployment instructions instead of using blueprint"
                echo "  --skip-env-check      Skip environment variables validation"
                echo "  --skip-project-check  Skip project validation (useful if projects list hangs)"
                echo "  --help, -h            Show this help message"
                echo ""
                echo "Example:"
                echo "  $0                          # Deploy using blueprint"
                echo "  $0 --manual                 # Show manual deployment instructions"
                echo "  $0 --skip-project-check     # Skip project check if it hangs"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Validation steps
    print_status "Validating deployment requirements..."
    check_render_cli
    check_render_auth
    
    if [[ "$SKIP_PROJECT_CHECK" == "false" ]]; then
        check_render_project
    else
        print_warning "Skipping project check as requested"
    fi
    
    validate_files
    
    if [[ "$SKIP_ENV_CHECK" == "false" ]]; then
        if ! check_env_vars; then
            print_warning "Environment variables not configured. Continuing with deployment setup..."
        fi
    fi
    
    if [[ "$MANUAL_MODE" == "true" ]]; then
        deploy_manual
    else
        deploy_blueprint
    fi
    
    show_post_deployment
}

# Run main function with all arguments
main "$@"