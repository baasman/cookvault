# Cookbook Creator Load Testing Suite

## Overview

This comprehensive load testing suite is designed to stress test the Cookbook Creator application, with a special focus on the memory-intensive recipe upload feature. The suite uses Locust for distributed load testing and provides detailed performance metrics and reports.

## Features

- **Multiple test scenarios**: baseline, stress, spike, endurance, and burst patterns
- **Real image uploads**: Uses actual recipe images (3-5MB each)
- **Multi-user simulation**: Supports concurrent users with different behavior patterns
- **Comprehensive reporting**: HTML reports with charts and performance metrics
- **Memory monitoring**: Tracks memory usage during image processing
- **OCR load testing**: Tests the OCR processing pipeline under load

## Installation

1. **Install dependencies:**
```bash
cd cookbook-creator
uv sync --group load-test
```

2. **Setup test users:**
```bash
# Create test users in your local environment
python scripts/setup_test_users.py --url http://localhost:5001

# For production testing (be careful!)
python scripts/setup_test_users.py --url https://your-production-url.com
```

## Configuration

The test suite uses the following configuration files:

- `scripts/load_test_config.yaml` - Main configuration file
- `scripts/test_users.json` - Test user credentials
- `backend/scripts/seed_data/` - Test images

### Test Images

- **Single upload**: `brussel-sprouts-browned-butter-black-garlic.jpg` (3.3MB)
- **Multi-upload**: `bolognese-1.jpg` (4.9MB) + `bolognese-2.jpg` (4.7MB)

## Running Tests

### Quick Start (Web UI)

```bash
# Start Locust with web interface
locust -f scripts/load_test.py --host=http://localhost:5001

# Open browser to http://localhost:8089
# Configure number of users and spawn rate
# Start the test
```

### Command Line (Headless)

```bash
# Baseline test (10 users, 5 minutes)
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless

# Stress test (50 users, 10 minutes)
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=50 \
    --spawn-rate=5 \
    --run-time=10m \
    --headless

# Spike test (sudden load increase)
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=100 \
    --spawn-rate=20 \
    --run-time=5m \
    --headless
```

### Test Scenarios

1. **Baseline Test**
   - 10 users, moderate load
   - Mix of uploads and browsing
   - Duration: 5 minutes

2. **Stress Test**
   - 50 concurrent users
   - Aggressive upload patterns
   - Duration: 10 minutes

3. **Spike Test**
   - Sudden increase from 5 to 50 users
   - Tests system response to traffic spikes
   - Duration: 5 minutes

4. **Endurance Test**
   - 20 users for 1 hour
   - Detects memory leaks
   - Monitor resource usage over time

5. **Burst Pattern**
   - Simulates real-world burst traffic
   - Random spikes in upload activity
   - Duration: 15 minutes

## Generating Reports

After running tests, generate comprehensive HTML reports:

```bash
# Generate report from latest test results
python scripts/load_test_report.py

# Reports will be saved in scripts/reports/
# Browser will automatically open the HTML report
```

### Report Contents

- **Performance Metrics**: Response times, throughput, error rates
- **System Metrics**: CPU, memory, network usage
- **Charts**: Response time distribution, throughput over time, memory trends
- **Error Analysis**: Breakdown of error types and frequencies
- **Recommendations**: Automated suggestions based on test results

## Monitoring During Tests

### Real-time Metrics (Web UI)

1. Open http://localhost:8089
2. View real-time charts and statistics
3. Download CSV data for analysis

### System Monitoring

```bash
# Monitor server memory in another terminal
watch -n 1 'ps aux | grep python | grep -E "(run|gunicorn)"'

# Monitor database connections
psql cookbook_db -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor Redis
redis-cli monitor
```

## Test User Management

### Create Test Users

```bash
python scripts/setup_test_users.py
```

### User Tiers

- **Free users**: Limited to 10 uploads/month
- **Premium users**: Unlimited uploads
- **Admin users**: Full system access

## Troubleshooting

### Common Issues

1. **"Upload limit reached" errors**
   - Free tier users hit monthly limit
   - Use premium test users or reset counters

2. **High memory usage**
   - OCR processing is memory-intensive
   - Monitor with `htop` or system monitor
   - Adjust `MAX_UPLOAD_SIZE` in .env

3. **Connection errors**
   - Check server is running
   - Verify database connections
   - Check Redis availability

4. **Slow response times**
   - OCR processing bottleneck
   - Check Cloudinary API limits
   - Review database query performance

### Debug Mode

```bash
# Run with debug logging
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --loglevel DEBUG
```

## Performance Tuning Tips

### Application Settings

```bash
# .env settings for testing
MAX_UPLOAD_SIZE=8           # Limit file size
MAX_IMAGE_DIMENSION=1200    # Reduce image dimensions
JPEG_QUALITY=85            # Compress images
SKIP_IMAGE_PREPROCESSING=true  # Skip heavy processing
```

### Database Optimization

```sql
-- Check slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Monitor connections
SELECT count(*) FROM pg_stat_activity;
```

### Redis Optimization

```bash
# Monitor memory usage
redis-cli INFO memory

# Clear cache if needed
redis-cli FLUSHDB
```

## Results Analysis

### Key Metrics to Monitor

1. **Response Times**
   - p50 < 1s (median)
   - p95 < 5s (95th percentile)
   - p99 < 10s (99th percentile)

2. **Error Rate**
   - < 1% for normal operation
   - < 5% under stress

3. **Throughput**
   - > 10 requests/second baseline
   - Monitor degradation under load

4. **Memory Usage**
   - < 1GB per worker process
   - No memory leaks over time

### Performance Baselines

| Scenario | Users | Target RPS | Max Response Time | Max Error Rate |
|----------|-------|------------|-------------------|----------------|
| Baseline | 10    | 15         | 3s                | 1%             |
| Stress   | 50    | 50         | 5s                | 5%             |
| Spike    | 100   | 75         | 10s               | 10%            |

## Advanced Usage

### Custom User Behaviors

Edit `scripts/load_test.py` to add custom behaviors:

```python
@task(weight)
def custom_behavior(self):
    # Your custom test logic
    pass
```

### Distributed Testing

Run on multiple machines:

```bash
# Master node
locust -f scripts/load_test.py --master

# Worker nodes
locust -f scripts/load_test.py --worker --master-host=<master-ip>
```

## Safety Considerations

⚠️ **WARNING**: These tests can generate significant load!

- Always test in a dedicated environment first
- Monitor server resources during tests
- Have a kill switch ready
- Don't run against production without approval
- Be aware of API rate limits (Cloudinary, Anthropic)

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs
3. Monitor system resources
4. Adjust test parameters as needed

---

Happy Testing! 🚀