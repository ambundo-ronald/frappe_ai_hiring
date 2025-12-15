# Docker Restart Guide - Quick Fix

## 🔧 Issues Fixed

1. **Database Connection**: ERPNext now connects to `mariadb` hostname (not 127.0.0.1)
2. **Redis Connection**: ERPNext now connects to `redis-cache` and `redis-queue` hostnames
3. **Port Conflict**: Nginx now uses port 8080 instead of 80 (Windows compatibility)
4. **Procfile Error**: Changed from `bench start` to `bench serve` command

## 🚀 Fresh Start Instructions

### 1. Stop and Clean Everything

```powershell
# Stop all containers
docker compose down

# Remove volumes (WARNING: This deletes all data!)
docker compose down -v

# Verify everything is stopped
docker ps -a | findstr erpnext
```

### 2. Start Fresh

```powershell
# Make sure your .env file has the OpenAI API key
# OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE

# Start the stack
docker compose up -d

# Watch the logs (IMPORTANT - wait for site creation)
docker compose logs -f erpnext
```

### 3. Wait for Initialization

Watch for these messages in the logs:

```
✓ Waiting for database to be ready...
✓ Creating new site...
✓ Configuring site...
✓ Installing ERPNext...
✓ Starting ERPNext web server...
```

**First-time setup takes 5-10 minutes!**

### 4. Verify Connections

```powershell
# Check if all containers are healthy
docker compose ps

# Check erpnext logs for errors
docker compose logs erpnext | findstr "ERROR"

# Check worker logs
docker compose logs worker | findstr "ERROR"

# Test database connection
docker exec erpnext_backend bench --site localhost mariadb
# Type: SELECT 1;
# Then: exit
```

### 5. Access ERPNext

Once you see "Starting ERPNext web server..." in the logs:

- **Direct Access**: http://localhost:8000
- **Via Nginx**: http://localhost:8080

**Login Credentials**:
- Username: `Administrator`
- Password: `admin`

## 🐛 Common Issues After Restart

### Issue: Site Already Exists Error

```powershell
# Remove the existing site volume
docker compose down -v
docker compose up -d
```

### Issue: Worker Still Shows Redis Error

```powershell
# Restart worker and scheduler after site is created
docker compose restart worker scheduler

# Check logs
docker compose logs worker
```

### Issue: Port 8080 Already in Use

Edit `docker-compose.yml`:

```yaml
nginx:
  ports:
    - "8081:80"  # Change 8080 to 8081
```

### Issue: Can't Access at localhost:8000

```powershell
# Check if backend is running
docker compose ps erpnext

# Check logs for errors
docker compose logs erpnext

# Try restarting just the backend
docker compose restart erpnext
```

## 📋 Verification Checklist

After starting the stack, verify:

- [ ] All 7 containers are running: `docker compose ps`
- [ ] MariaDB is healthy: `docker compose ps mariadb`
- [ ] Redis Cache is healthy: `docker compose ps redis-cache`
- [ ] Redis Queue is healthy: `docker compose ps redis-queue`
- [ ] ERPNext backend shows no errors: `docker compose logs erpnext | findstr "ERROR"`
- [ ] Worker shows no Redis errors: `docker compose logs worker | findstr "ERROR"`
- [ ] Can access UI at http://localhost:8000
- [ ] Can log in with Administrator/admin

## 🔍 Debug Commands

```powershell
# Enter the backend container
docker exec -it erpnext_backend bash

# Inside container - check site config
cat sites/localhost/site_config.json

# Should show:
# {
#   "db_host": "mariadb",
#   "db_port": 3306,
#   "redis_cache": "redis://redis-cache:6379",
#   "redis_queue": "redis://redis-queue:6379",
#   ...
# }

# Test database connection
bench --site localhost mariadb

# Check bench status
bench status

# View site list
bench --site localhost list-apps
```

## ⏱️ Expected Timeline

| Step | Time | What's Happening |
|------|------|------------------|
| Database startup | 10-15s | MariaDB initializing |
| Redis startup | 5s | Redis Cache & Queue ready |
| Site creation | 2-3min | Creating database, installing apps |
| ERPNext install | 3-5min | Installing ERPNext app |
| AI Hiring install | 1-2min | Installing custom app |
| Server start | 10s | Web server ready |
| **Total** | **5-10min** | First run only |

Subsequent starts: ~30 seconds

## 🎯 Next Steps After Successful Start

1. Log in to ERPNext
2. Configure AI Settings (see DOCKER_SETUP.md)
3. Create a test Job Opening
4. Upload a test candidate resume
5. Monitor background jobs in logs

## 📞 Still Having Issues?

Check the main troubleshooting section in `DOCKER_SETUP.md` or:

1. Share the output of: `docker compose logs --tail=50`
2. Check: `docker compose ps` - all containers should show "healthy" or "running"
3. Verify `.env` file exists with valid `OPENAI_API_KEY`
