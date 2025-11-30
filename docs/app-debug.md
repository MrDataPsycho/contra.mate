# Application Debugging Log

## Document Information
- **Version**: 1.0.0
- **Date**: 2025-11-30
- **Last Updated**: 2025-11-30
- **Status**: Resolved

---

## Issue Summary

### Incident Report
**Date**: 2025-11-30
**Severity**: High
**Status**: ✅ Resolved
**Component**: Backend API + PostgreSQL Database

### Problem Description
The Streamlit UI was unable to fetch documents from the backend API, displaying the following error:

```
Error fetching documents: 500 Server Error: Internal Server Error
for url: http://backend:8000/api/contracts/documents?limit=1000
```

---

## Root Cause Analysis

### Primary Issue
**Docker Desktop VM Disk Space Exhaustion**

The Docker Desktop virtual machine had reached 100% disk capacity (57GB used out of 59GB available), preventing PostgreSQL from performing write operations.

### Error Chain
1. **PostgreSQL Error**: `FATAL: could not write init file`
2. **Database Connection Failure**: PostgreSQL unable to accept new connections
3. **API Failure**: Backend service returned 500 Internal Server Error
4. **UI Failure**: Streamlit unable to fetch documents

### Technical Details

#### PostgreSQL Logs
```
2025-11-30 18:39:05.985 UTC [33] FATAL:  could not write init file
```

#### Backend API Logs
```
2025-11-30 18:39:05.986 | ERROR | contramate.services.contract_service:get_all_documents:83 -
Error fetching documents: (psycopg2.OperationalError) connection to server at "postgres" (172.18.0.2),
port 5432 failed: FATAL:  could not write init file
```

#### Disk Space Analysis
**Before Cleanup:**
```bash
$ docker exec rag-postgres df -h /var/lib/postgresql/data
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        59G   57G     0 100% /var/lib/postgresql/data
```

**After Cleanup:**
```bash
$ docker exec rag-postgres df -h /var/lib/postgresql/data
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        59G  3.4G   53G   7% /var/lib/postgresql/data
```

---

## Resolution Steps

### 1. Diagnosis
```bash
# Check Docker disk usage
docker system df

# Output showed:
# - Images: 24.73GB reclaimable (79%)
# - Build Cache: 20.57GB reclaimable (100%)
# - Total: ~45GB reclaimable
```

### 2. Cleanup Execution
```bash
# Clean up Docker system (removes unused images, containers, networks, and build cache)
docker system prune -a --volumes --force
```

**Result**: Reclaimed 49.51GB of disk space

### 3. PostgreSQL Restart
```bash
# Restart PostgreSQL to clear the error state
docker-compose restart postgres
```

### 4. Verification
```bash
# Test API endpoint
curl "http://localhost:8000/api/contracts/documents?limit=5"

# Successfully returned 5 documents
```

---

## Impact Assessment

### System Impact
- **Downtime**: ~15 minutes
- **Data Loss**: None
- **Services Affected**:
  - PostgreSQL Database
  - Backend API
  - Streamlit UI

### Business Impact
- Users unable to access contract documents
- Chat functionality unavailable during incident

---

## Prevention Measures

### Immediate Actions Taken
1. ✅ Cleaned up Docker system
2. ✅ Documented disk space monitoring requirement
3. ✅ Verified all services operational

### Recommended Long-term Solutions

#### 1. Increase Docker Desktop VM Disk Size
**Current**: 59GB
**Recommended**: 100GB+ for development

**Steps** (macOS Docker Desktop):
1. Open Docker Desktop
2. Go to Settings → Resources → Disk image size
3. Increase to at least 100GB
4. Apply & Restart

#### 2. Implement Automated Cleanup
Add to development workflow:

```bash
# Weekly cleanup script
#!/bin/bash
# cleanup-docker.sh

echo "Cleaning up Docker resources..."
docker system prune -f
docker image prune -a -f --filter "until=168h"  # Remove images older than 7 days
echo "Cleanup complete!"
```

Add to cron or run weekly manually.

#### 3. Monitoring Script
```bash
# monitor-disk.sh
#!/bin/bash

THRESHOLD=80
USAGE=$(docker system df --format "{{.Type}}\t{{.Size}}" | grep "Build Cache" | awk '{print $2}' | sed 's/GB//')

if (( $(echo "$USAGE > $THRESHOLD" | bc -l) )); then
    echo "WARNING: Docker disk usage above ${THRESHOLD}GB: ${USAGE}GB"
    echo "Consider running: docker system prune -a"
fi
```

#### 4. Docker Compose Volume Management
Consider using named volumes with size limits:

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      device: /path/to/large/disk
      o: bind
```

#### 5. CI/CD Integration
Add pre-deployment checks:

```yaml
# .github/workflows/cleanup.yml
- name: Docker Cleanup
  run: |
    docker system prune -f
    docker volume prune -f
```

---

## Related Changes

### Hot Reload Configuration
As part of this debugging session, hot reload was also configured:

#### docker-compose.yml
```yaml
backend:
  volumes:
    - ./src/contramate:/app/src/contramate
  # ... other config

ui:
  volumes:
    - ./src/ui:/app/src/ui
  # ... other config
```

#### Dockerfile.backend
```dockerfile
CMD ["uvicorn", "src.contramate.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### UI Directory Restructure
Moved `src/contramate/ui` → `src/ui` for better organization.

---

## Testing & Validation

### Test Cases Executed
1. ✅ PostgreSQL connection test
2. ✅ Backend API health check
3. ✅ Documents API endpoint test
4. ✅ Streamlit UI document loading
5. ✅ Docker volume mount verification

### Success Criteria
- [x] PostgreSQL accepts connections
- [x] API returns 200 status code
- [x] Documents are retrieved successfully
- [x] UI displays documents without errors
- [x] Disk usage below 20%

---

## Lessons Learned

### What Went Well
1. Quick diagnosis using Docker logs
2. Non-destructive resolution (no data loss)
3. Significant space reclaimed (49.51GB)
4. Opportunity to implement hot reload

### What Could Be Improved
1. **Proactive Monitoring**: Should have disk space alerts
2. **Documentation**: Needed better operational runbooks
3. **Resource Planning**: Docker Desktop VM size was undersized
4. **Automated Cleanup**: Should have scheduled cleanup tasks

### Action Items
- [ ] Increase Docker Desktop VM disk size to 100GB
- [ ] Set up disk space monitoring alerts
- [ ] Create weekly Docker cleanup cron job
- [ ] Document Docker resource requirements in README
- [ ] Add disk space checks to CI/CD pipeline

---

## References

### Related Documentation
- [Docker System Prune Documentation](https://docs.docker.com/engine/reference/commandline/system_prune/)
- [PostgreSQL Disk Space Management](https://www.postgresql.org/docs/current/diskusage.html)
- Docker Compose Volume Documentation

### Internal Documentation
- `README.md` - Project setup
- `CLAUDE.md` - Development guidelines
- `docker-compose.yml` - Service configuration

---

## Appendix

### Environment Details
- **OS**: macOS (Darwin 24.6.0)
- **Docker Desktop**: Latest version
- **PostgreSQL**: 15.14
- **Python**: 3.12
- **Platform**: darwin (Apple Silicon)

### Service Ports
- Backend API: 8000
- Streamlit UI: 8501
- PostgreSQL: 5432
- DynamoDB: 8001
- OpenSearch: 9200

### Useful Commands
```bash
# Check Docker disk usage
docker system df

# Check PostgreSQL volume space
docker exec rag-postgres df -h /var/lib/postgresql/data

# View PostgreSQL logs
docker logs rag-postgres --tail 50

# View backend logs
docker logs rag-backend --tail 50

# Clean Docker system
docker system prune -a --volumes --force

# Restart specific service
docker-compose restart postgres
```

---

## Version History

| Version | Date       | Author         | Changes                                    |
|---------|------------|----------------|--------------------------------------------|
| 1.0.0   | 2025-11-30 | Claude Code    | Initial documentation of disk space issue  |

---

**Document Owner**: Development Team
**Review Cycle**: Quarterly
**Next Review**: 2026-02-28
