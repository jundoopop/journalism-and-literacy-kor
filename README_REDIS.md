# Redis Setup Guide

This project uses Redis for caching LLM analysis results to reduce API costs and improve performance.

## Quick Start

### Using Docker Compose (Recommended)

**Start Redis:**
```bash
docker-compose up -d
```

**Check Status:**
```bash
docker-compose ps
```

**View Logs:**
```bash
docker-compose logs redis
```

**Stop Redis:**
```bash
docker-compose down
```

**Stop and Remove Data:**
```bash
docker-compose down -v
```

---

## Manual Redis Installation

### macOS (Homebrew)
```bash
brew install redis
brew services start redis
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Windows
Download from: https://redis.io/download

Or use WSL2 with Ubuntu instructions above.

---

## Configuration

Redis settings are configured in `.env`:

```bash
# Redis Cache Configuration
CACHE_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=optional_password
CACHE_TTL=3600  # 1 hour default
```

---

## Testing Redis Connection

**Test with redis-cli:**
```bash
# Connect
redis-cli

# Test commands
> PING
PONG

> SET test "hello"
OK

> GET test
"hello"

> DEL test
(integer) 1

> EXIT
```

**Test with Python:**
```bash
cd scripts
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())  # Should print: True
"
```

---

## Cache Management

### View Cache Stats
```bash
# Using admin API (requires admin token)
curl -H "X-Admin-Token: your_token" \
  http://localhost:5001/admin/cache/stats

# Using redis-cli
redis-cli
> INFO stats
> DBSIZE
```

### Clear Cache
```bash
# Using admin API
curl -X POST \
  -H "X-Admin-Token: your_token" \
  http://localhost:5001/admin/cache/clear

# Clear all cache
curl -X POST \
  -H "X-Admin-Token: your_token" \
  http://localhost:5001/admin/cache/clear?pattern=*

# Using redis-cli
redis-cli FLUSHDB
```

### Monitor Cache Activity
```bash
# Real-time monitoring
redis-cli MONITOR

# Watch specific keys
redis-cli
> KEYS article:*
```

---

## Cache Strategy

### Cache Keys Format
```
article:{url_hash}:providers:{sorted_provider_list}:v1
```

**Examples:**
- `article:abc123:providers:gemini:v1` - Single Gemini analysis
- `article:abc123:providers:gemini,mistral:v1` - Consensus analysis

### TTL (Time To Live)
- Default: 3600 seconds (1 hour)
- Configurable via `CACHE_TTL` environment variable
- Articles auto-expire after TTL

### Eviction Policy
- **Policy**: `allkeys-lru` (Least Recently Used)
- **Max Memory**: 256MB (configurable in docker-compose.yml)
- When memory is full, least recently used keys are evicted

---

## Performance Benefits

### Expected Impact
- **Cache Hit Rate**: 40-50% for typical usage
- **Response Time**: 10-50ms (cached) vs 2-5s (LLM API)
- **API Cost Savings**: 40-50% reduction in LLM API calls
- **Concurrent Requests**: Better handling of multiple requests for same article

### Monitoring
Track cache performance via:
1. **Admin API**: `/admin/metrics` shows cache hit/miss rates
2. **Logs**: JSON logs include cache status for each request
3. **Database**: RequestLog table tracks cache hits

---

## Troubleshooting

### Redis Not Starting

**Check if port is in use:**
```bash
lsof -i :6379
```

**Check Docker logs:**
```bash
docker-compose logs redis
```

**Restart Redis:**
```bash
docker-compose restart redis
```

### Connection Refused

1. Check Redis is running: `docker-compose ps`
2. Check `REDIS_HOST` in `.env` (should be `localhost`)
3. Check firewall settings
4. Test connection: `redis-cli ping`

### Cache Not Working

1. Check `CACHE_ENABLED=True` in `.env`
2. Check server logs for cache errors
3. Verify Redis connection: `redis-cli ping`
4. Check admin metrics: `/admin/metrics`

### High Memory Usage

1. Check current memory: `redis-cli INFO memory`
2. Reduce `CACHE_TTL` to expire keys faster
3. Reduce `maxmemory` in docker-compose.yml
4. Clear cache: `redis-cli FLUSHDB`

---

## Production Considerations

### Security
- Set `REDIS_PASSWORD` for production
- Use firewall to restrict Redis port (6379)
- Consider Redis ACL for fine-grained access control

### Persistence
Current setup uses AOF (Append Only File) for persistence:
- Saves to disk every 60 seconds if at least 1 key changed
- Data survives container restarts
- Stored in Docker volume `redis-data`

### Scaling
For production:
- Consider Redis Cluster for horizontal scaling
- Use Redis Sentinel for high availability
- Set up replication for redundancy

---

## Useful Commands

```bash
# Docker Compose
docker-compose up -d          # Start Redis
docker-compose down           # Stop Redis
docker-compose logs -f redis  # Follow logs
docker-compose restart redis  # Restart Redis

# Redis CLI
redis-cli                     # Connect to Redis
redis-cli FLUSHDB             # Clear current database
redis-cli FLUSHALL            # Clear all databases
redis-cli DBSIZE              # Count keys
redis-cli INFO                # Server info
redis-cli MONITOR             # Monitor commands

# Cache Management
redis-cli KEYS "article:*"    # List all article caches
redis-cli TTL key_name        # Check time to live
redis-cli DEL key_name        # Delete specific key
```

---

## Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [Redis Best Practices](https://redis.io/topics/best-practices)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
