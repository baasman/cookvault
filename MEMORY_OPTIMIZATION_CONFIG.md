# Memory Optimization Configuration

## Environment Variables for Render Dashboard

Add these environment variables to your **backend service** in Render dashboard:

```bash
# Memory Optimization Settings
MAX_UPLOAD_SIZE=8                    # Max file size in MB (reduced from 15MB)
MAX_IMAGE_DIMENSION=1200             # Max image dimension in pixels (reduced from 1568)
JPEG_QUALITY=85                      # JPEG compression quality (85% for balance)
SKIP_IMAGE_PREPROCESSING=true        # Skip heavy scikit-image processing

# Worker Timeout Settings (NEW - Required)
GUNICORN_TIMEOUT=120                 # 2 minutes for LLM processing

# Existing CORS setting
CORS_ORIGINS=https://cookvault-frontend.onrender.com
```

Add this environment variable to your **frontend service** in Render dashboard:

```bash
# Frontend API Configuration  
VITE_API_URL=https://cookvault-exaq.onrender.com/api
```

## Memory Usage Improvements

### Before Optimizations:
- **Memory spike**: 512MB per upload (causing crashes)
- **Processing**: Dual OCR paths (pytesseract + LLM)
- **Image handling**: Full resolution processing
- **API calls**: 2 separate LLM calls (extract + parse)

### After Optimizations:
- **Expected memory**: 150-200MB per upload (60% reduction)
- **Processing**: LLM-only OCR path
- **Image handling**: Aggressive resizing and compression
- **API calls**: Single LLM call combining extract + parse
- **Memory management**: Explicit garbage collection

## Key Optimizations Applied:

1. ✅ **Aggressive Image Resizing**: Max 1200px instead of 1568px
2. ✅ **JPEG Compression**: 85% quality reduces file sizes by 30-50%
3. ✅ **Eliminated pytesseract**: Removed memory-intensive traditional OCR
4. ✅ **Single-pass LLM**: Extract + parse in one call (50% fewer API calls)
5. ✅ **Chunked Base64 encoding**: 1MB chunks instead of full-image encoding
6. ✅ **Explicit memory cleanup**: Garbage collection after each major step
7. ✅ **Stricter upload limits**: 8MB max file size instead of 15MB
8. ✅ **Asynchronous Processing**: Upload returns immediately, processing happens in background
9. ✅ **Worker Timeout Fix**: Increased from 30s to 2 minutes for LLM processing

## Expected Results:
- No more 502 Bad Gateway errors
- Faster upload processing (30-40% improvement)
- More reliable service on Render Starter tier
- Better image quality with LLM-only extraction
- Reduced API costs (fewer LLM calls)

## Monitoring:
Check your Render service logs for these new log messages:
- `"Preparing image for LLM: [image_path]"`
- `"Compressed image size: X.XMB (reduction: XX.X%)"`
- `"Starting single-pass LLM extract+parse operation"`
- `"Single-pass LLM extract+parse completed successfully"`

These logs will help you verify the optimizations are working correctly.