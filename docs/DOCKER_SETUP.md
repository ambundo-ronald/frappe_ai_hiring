# Docker Setup Guide for AI Hiring Automation

This guide will help you set up a local testing environment using Docker Compose with ERPNext v15.25.0.

## 📋 Prerequisites

- **Docker Desktop** (Windows/Mac) or Docker Engine (Linux)
- **Docker Compose** v2.0+
- Minimum **8GB RAM** allocated to Docker
- **20GB** free disk space
- **OpenAI API Key** (for AI features)

### Check Docker Installation

```powershell
# Check Docker version
docker --version
# Should show: Docker version 20.10.x or higher

# Check Docker Compose version
docker compose version
# Should show: Docker Compose version v2.x.x or higher
```

## 🚀 Quick Start

### 1. Configure Environment Variables

Create a `.env` file from the example:

```powershell
# Copy example file
Copy-Item .env.example .env

# Edit .env and add your OpenAI API key
notepad .env
```

**Update the following in `.env`**:
```env
OPENAI_API_KEY=sk-proj-YOUR-ACTUAL-API-KEY-HERE
```

### 2. Start the Stack

```powershell
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Wait for initialization (first run takes 5-10 minutes)
# Watch for "Starting ERPNext..." message
```

### 3. Access ERPNext

Once the containers are running:

- **ERPNext UI (Direct)**: http://localhost:8000
- **Via Nginx (Recommended)**: http://localhost:8080

**Default Credentials**:
- Username: `Administrator`
- Password: `admin`

### 4. Manual App Installation (if needed)

If the AI Hiring app wasn't auto-installed:

```powershell
# Enter the container
docker exec -it erpnext_backend bash

# Inside container
cd /home/frappe/frappe-bench

# Get the app
bench get-app /home/frappe/frappe-bench/apps/ai_hiring

# Install on site
bench --site localhost install-app ai_hiring

# Migrate
bench --site localhost migrate

# Exit container
exit

# Restart services
docker compose restart erpnext worker scheduler
```

## 📦 Container Overview

The stack includes 7 containers:

| Container | Description | Ports |
|-----------|---------|------|
| `erpnext_mariadb` | MariaDB 10.6 database | 3306 (internal) |
| `erpnext_redis_cache` | Redis cache | 6379 (internal) |
| `erpnext_redis_queue` | Redis queue | 6379 (internal) |
| `erpnext_backend` | ERPNext application | 8000, 9000 |
| `erpnext_worker` | Background worker | - |
| `erpnext_scheduler` | Scheduled jobs | - |
| `erpnext_nginx` | Nginx reverse proxy | 8080 (changed from 80) |

## 🔧 Configuration

### Configure AI Settings

1. Log in to ERPNext: http://localhost:8000
2. Navigate to **Search** → Type "AI Settings"
3. Configure:
   - **API Provider**: OpenAI
   - **API Key**: (auto-loaded from environment)
   - **Model Name**: gpt-4 or gpt-3.5-turbo
   - **Temperature**: 0.2
   - **Enable Rate Limiting**: Yes
   - **Hourly Limit**: 100
   - **Daily Limit**: 500
4. Click **Test Configuration** to verify
5. Save

### Enable Developer Mode

Developer mode is enabled by default. To verify:

```powershell
docker exec -it erpnext_backend bash

# Check site config
cat sites/localhost/site_config.json

# Should show: "developer_mode": 1
```

## 🧪 Testing the AI Hiring App

### Create Test Job Opening

1. Go to **HRMS** → **Job Opening** → **New**
2. Fill in details:
   ```
   Job Title: Senior Python Developer
   Description: 
   We are seeking an experienced Python developer with:
   - 5+ years of Python experience
   - Strong Django/Flask expertise
   - Experience with REST APIs
   - Knowledge of PostgreSQL
   - Familiarity with Docker and AWS
   ```
3. Save

### Create Test Candidate

1. Go to **HRMS** → **Job Applicant** → **New**
2. Fill in:
   ```
   Applicant Name: Test Candidate
   Email: test@example.com
   Job Title: Senior Python Developer (link to job opening)
   ```
3. **Attach Resume**: Upload a sample resume (PDF/DOCX)
4. Save

### Verify Processing

The system should automatically:
- Parse the resume
- Evaluate the candidate
- Generate questions (if shortlisted)

**Check Progress**:
1. Open the Job Applicant record
2. Scroll to **AI Resume Parsing** section
3. View **AI Shortlisting Result**
4. Check **AI Questionnaire** (if shortlisted)

**View Logs**:
```powershell
# Application logs
docker compose logs -f erpnext

# Worker logs (background jobs)
docker compose logs -f worker

# All logs
docker compose logs -f
```

## 🛠️ Common Commands

### Container Management

```powershell
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart erpnext

# View running containers
docker compose ps

# View logs
docker compose logs -f [service_name]

# Stop and remove everything (including volumes)
docker compose down -v
```

### Access Containers

```powershell
# ERPNext backend
docker exec -it erpnext_backend bash

# Database
docker exec -it erpnext_mariadb mysql -uroot -padmin

# Redis cache
docker exec -it erpnext_redis_cache redis-cli
```

### Bench Commands (inside container)

```powershell
# Enter container
docker exec -it erpnext_backend bash

# Common bench commands
bench --site localhost migrate
bench --site localhost clear-cache
bench --site localhost console
bench --site localhost backup
bench restart

# Run tests
bench --site localhost run-tests --app ai_hiring

# Check job queue
bench --site localhost doctor

# View background jobs
bench --site localhost console
>>> frappe.db.get_all("RQ Job", fields=["name", "status", "job_name"], limit=20)
```

### Database Access

```powershell
# Access MariaDB
docker exec -it erpnext_mariadb mysql -uroot -padmin erpnext

# Inside MySQL
SHOW TABLES LIKE '%ai%';
SELECT * FROM `tabAI Settings`;
SELECT * FROM `tabAI Audit Log` LIMIT 10;
```

## 🐛 Troubleshooting

### Issue: Containers won't start

**Check Docker resources**:
- Ensure Docker has at least 8GB RAM allocated
- Check available disk space

```powershell
# View Docker resource usage
docker stats

# Check disk space
docker system df
```

### Issue: ERPNext not accessible

**Check logs**:
```powershell
# View ERPNext logs
docker compose logs erpnext

# Check if services are healthy
docker compose ps
```

**Restart services**:
```powershell
docker compose restart erpnext worker scheduler
```

### Issue: AI Hiring app not found

**Install manually**:
```powershell
docker exec -it erpnext_backend bash
cd /home/frappe/frappe-bench
bench get-app /home/frappe/frappe-bench/apps/ai_hiring
bench --site localhost install-app ai_hiring
bench --site localhost migrate
exit
docker compose restart erpnext
```

### Issue: Background jobs not processing

**Check worker**:
```powershell
# View worker logs
docker compose logs -f worker

# Restart worker
docker compose restart worker

# Inside container, check queue
docker exec -it erpnext_backend bench --site localhost doctor
```

### Issue: Database connection errors

**Check MariaDB**:
```powershell
# View MariaDB logs
docker compose logs mariadb

# Test connection
docker exec -it erpnext_mariadb mysql -uroot -padmin -e "SHOW DATABASES;"
```

### Issue: API key not working

**Verify environment variable**:
```powershell
# Check if .env file exists
cat .env

# Restart to reload environment
docker compose down
docker compose up -d
```

**Set API key in ERPNext**:
1. Navigate to AI Settings
2. Manually enter API key
3. Click Test Configuration

### Issue: Out of memory errors

**Increase Docker memory**:
- Docker Desktop → Settings → Resources
- Increase Memory to 8GB or more
- Click Apply & Restart

## 🔄 Data Persistence

Data is persisted in Docker volumes:

```powershell
# List volumes
docker volume ls | Select-String "frappe_ai_hiring"

# Backup data
docker compose exec mariadb mysqldump -uroot -padmin erpnext > backup.sql

# Restore data
Get-Content backup.sql | docker compose exec -T mariadb mysql -uroot -padmin erpnext
```

## 🧹 Cleanup

### Remove Containers Only

```powershell
docker compose down
```

### Remove Containers and Volumes (Full Reset)

```powershell
# WARNING: This deletes all data!
docker compose down -v

# Remove images too
docker compose down -v --rmi all
```

## 📊 Performance Tips

### Optimize for Development

1. **Disable Nginx** (if not needed):
   ```yaml
   # Comment out in docker-compose.yml
   # nginx:
   #   ...
   ```

2. **Reduce Worker Processes**:
   ```powershell
   docker exec -it erpnext_backend bench --site localhost set-config background_workers 2
   ```

3. **Increase Shared Memory**:
   Add to docker-compose.yml under erpnext service:
   ```yaml
   shm_size: '2gb'
   ```

### Monitor Resource Usage

```powershell
# Real-time stats
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

## 🔐 Security Notes

**For Testing Only**:
- Default passwords are weak (admin/admin)
- Developer mode is enabled
- Not suitable for production use

**Before Production**:
- Change all default passwords
- Disable developer mode
- Use environment-specific .env files
- Enable SSL/TLS
- Review security settings in SECURITY.md

## 📝 Testing Checklist

Before deploying to production, verify:

- [ ] Resume parsing works (PDF, DOCX, TXT)
- [ ] Candidate shortlisting generates scores
- [ ] Questions are generated for shortlisted candidates
- [ ] Email notifications are sent
- [ ] Background jobs process correctly
- [ ] Reports display data
- [ ] Dashboard shows metrics
- [ ] API endpoints respond correctly
- [ ] Rate limiting functions
- [ ] Audit logs are created

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `docker compose logs -f`
2. **Review documentation**: USER_GUIDE.md, ADMIN_GUIDE.md
3. **Search issues**: Check GitHub issues
4. **Ask for help**: Create a new issue with logs

## 📚 Additional Resources

- **Frappe Docker**: https://github.com/frappe/frappe_docker
- **ERPNext Documentation**: https://docs.erpnext.com
- **Docker Compose Docs**: https://docs.docker.com/compose/

---

## 🎯 Next Steps After Testing

Once testing is successful:

1. **Review Results**: Check AI accuracy and performance
2. **Adjust Settings**: Fine-tune rate limits and prompts
3. **Train Users**: Use USER_GUIDE.md for training
4. **Plan Deployment**: Review ADMIN_GUIDE.md for production setup
5. **Configure Security**: Follow SECURITY.md guidelines

---

**Happy Testing! 🚀**

For production deployment, refer to ADMIN_GUIDE.md for best practices and configuration.
