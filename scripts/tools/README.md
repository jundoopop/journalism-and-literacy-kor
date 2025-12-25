# CLI Admin Tools

Command-line tools for system management, debugging, and monitoring.

## Overview

The CLI admin tools provide interactive debugging and management capabilities for the News Literacy Highlighter system. These tools allow you to:

- View system metrics and analytics
- Query structured logs by correlation ID
- Manage feature flags
- Administer cache

## Tools

### 1. view_metrics.py

View system metrics and analytics from the database.

```bash
# View all metrics
python scripts/tools/view_metrics.py

# Metrics from last 24 hours
python scripts/tools/view_metrics.py --last 24h

# Filter by provider
python scripts/tools/view_metrics.py --provider gemini

# Filter by mode
python scripts/tools/view_metrics.py --mode consensus

# Combine filters
python scripts/tools/view_metrics.py --provider mistral --last 7d
```

**Output includes:**
- Request metrics (total, success rate, latency percentiles)
- LLM provider metrics (per-provider success rates and latencies)
- Error breakdown (error types and counts)

### 2. view_logs.py

Query structured logs and request traces.

```bash
# View logs by correlation ID (most common use case)
python scripts/tools/view_logs.py --correlation-id req_abc123

# View recent error logs
python scripts/tools/view_logs.py --last 1h --level ERROR

# Filter by component
python scripts/tools/view_logs.py --component llm.gemini --last 24h

# Filter by URL
python scripts/tools/view_logs.py --url "chosun.com" --last 1h

# Verbose mode (show extra fields)
python scripts/tools/view_logs.py --correlation-id req_abc123 --verbose
```

**Output includes:**
- Colored log entries with timestamps
- Request details from database
- Analysis results for each provider
- Full timeline for correlation ID traces

### 3. cache_admin.py

Manage Redis cache.

```bash
# View cache statistics
python scripts/tools/cache_admin.py stats

# Check cache health
python scripts/tools/cache_admin.py health

# Clear all cache (requires confirmation)
python scripts/tools/cache_admin.py clear

# Clear without confirmation
python scripts/tools/cache_admin.py clear --yes

# Invalidate specific URL
python scripts/tools/cache_admin.py invalidate "https://chosun.com/..."

# Invalidate specific provider combination
python scripts/tools/cache_admin.py invalidate "https://chosun.com/..." --providers gemini,mistral
```

**Output includes:**
- Cache hit/miss rates
- Redis connection status
- Redis memory usage
- Redis version and client info

### 4. feature_flags.py

Manage feature flags for controlling system behavior.

```bash
# List all feature flags
python scripts/tools/feature_flags.py list

# Get specific flag value
python scripts/tools/feature_flags.py get cache_enabled

# Set boolean flag
python scripts/tools/feature_flags.py set cache_enabled true
python scripts/tools/feature_flags.py set cache_enabled false

# Set flag with JSON config
python scripts/tools/feature_flags.py set new_feature '{"timeout": 30, "retries": 3}'

# Create new flag
python scripts/tools/feature_flags.py create use_new_prompt true --description "Enable new article analysis prompt"

# Create flag with config
python scripts/tools/feature_flags.py create llm_config '{"temperature": 0.2}' --description "LLM parameters"

# Delete (disable) flag
python scripts/tools/feature_flags.py delete old_feature --yes
```

**Output includes:**
- Flag name and enabled status
- Configuration values (JSON)
- Description
- Created/updated timestamps

## Common Workflows

### Debug a Failed Request

When a user reports an error with a specific correlation ID:

```bash
# 1. View logs for that request
python scripts/tools/view_logs.py --correlation-id req_abc123

# 2. Check provider metrics around that time
python scripts/tools/view_metrics.py --last 1h

# 3. View recent errors
python scripts/tools/view_logs.py --last 1h --level ERROR
```

### Monitor System Health

```bash
# 1. Check cache health and stats
python scripts/tools/cache_admin.py health
python scripts/tools/cache_admin.py stats

# 2. View overall metrics
python scripts/tools/view_metrics.py --last 24h

# 3. Check for errors
python scripts/tools/view_metrics.py --last 24h | grep -A 5 "Error Breakdown"
```

### Manage Features

```bash
# 1. List current feature flags
python scripts/tools/feature_flags.py list

# 2. Enable experimental feature
python scripts/tools/feature_flags.py create experiment_new_ui true --description "Test new UI layout"

# 3. Monitor performance
python scripts/tools/view_metrics.py --last 1h

# 4. Disable if issues arise
python scripts/tools/feature_flags.py set experiment_new_ui false
```

### Troubleshoot Cache Issues

```bash
# 1. Check cache health
python scripts/tools/cache_admin.py health

# 2. View cache statistics
python scripts/tools/cache_admin.py stats

# 3. Clear cache if stale data suspected
python scripts/tools/cache_admin.py clear --yes

# 4. Monitor hit rate improvement
python scripts/tools/cache_admin.py stats
```

## Tips

### Piping and Filtering

All tools output to stdout, so you can pipe to standard Unix tools:

```bash
# Search for specific errors
python scripts/tools/view_logs.py --last 24h --level ERROR | grep "timeout"

# Count requests by provider
python scripts/tools/view_metrics.py --last 7d | grep "Avg Latency"

# Export feature flags to file
python scripts/tools/feature_flags.py list > feature_flags_backup.txt
```

### Time Range Formats

The `--last` parameter accepts:
- `30m` - 30 minutes
- `1h` - 1 hour
- `24h` - 24 hours
- `7d` - 7 days
- `30d` - 30 days

### Correlation ID Format

Correlation IDs follow the format: `req_<12_hex_chars>`

Example: `req_a1b2c3d4e5f6`

You can find correlation IDs:
- In API responses (`correlation_id` field)
- In logs (`correlation_id` field)
- In error messages shown to users

## Configuration

All tools read from the same configuration as the main server:
- `.env` file for environment variables
- `scripts/config/settings.py` for defaults

Required configuration:
- Database path (default: `data/analytics.db`)
- Log directory (default: `logs/`)
- Redis host/port (for cache tools)

## Troubleshooting

### "Database not found"

Ensure the database has been initialized:
```bash
python scripts/server.py  # Run once to initialize database
```

### "Redis connection failed"

Start Redis via Docker Compose:
```bash
docker-compose up -d redis
```

Or check if Redis is running:
```bash
python scripts/tools/cache_admin.py health
```

### "Permission denied"

Make tools executable:
```bash
chmod +x scripts/tools/*.py
```

### "Module not found"

Ensure you're running from project root:
```bash
cd /path/to/project
python scripts/tools/view_metrics.py
```

## See Also

- [Architecture Plan](../../.claude/plans/groovy-honking-clock.md) - Overall system design
- [Redis Setup](../README_REDIS.md) - Redis configuration guide
- [Database Schema](../database/models.py) - Database models and schema
