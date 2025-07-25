# Ngrok HTTPS Setup

This setup uses ngrok to provide HTTPS access to your local development environment without managing certificates.

## Prerequisites

1. Install ngrok: https://ngrok.com/download
2. Create ngrok account and get auth token: https://dashboard.ngrok.com/get-started/your-authtoken

## Setup

1. **Configure ngrok auth token:**
   ```bash
   cp .env.ngrok .env.ngrok.local
   # Edit .env.ngrok.local and add your NGROK_AUTHTOKEN
   ```

2. **Start the services:**
   ```bash
   docker-compose -f docker-compose.ngrok.yml --env-file .env.ngrok.local up --build
   ```

3. **Get ngrok URLs:**
   - Backend ngrok interface: http://localhost:4040
   - Frontend ngrok interface: http://localhost:4041
   - Copy the HTTPS URLs from these interfaces

4. **Update environment with ngrok URLs:**
   - Edit `.env.ngrok.local`
   - Set `NGROK_BACKEND_URL` to your backend ngrok URL
   - Restart frontend container to pick up new API URL:
     ```bash
     docker-compose -f docker-compose.ngrok.yml restart frontend
     ```

## Usage

- **Frontend:** Access via ngrok frontend URL (e.g., https://abc123.ngrok.io)
- **Backend:** Access via ngrok backend URL (e.g., https://def456.ngrok.io)
- **Real HTTPS:** No certificate warnings, works with external services
- **External access:** Share URLs with others for testing

## Benefits

- ✅ Real HTTPS certificates (no browser warnings)
- ✅ External access for testing
- ✅ No certificate management
- ✅ Simple HTTP containers
- ✅ Easy debugging
- ✅ Works with webhooks and external services

## Monitoring

- Backend ngrok dashboard: http://localhost:4040
- Frontend ngrok dashboard: http://localhost:4041
- View requests, responses, and replay functionality