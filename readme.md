## 🚖 Taxi trip enterprise project

## 🎯 Goals project

## 🚀 Build taxi tracking for similar in tracking ride
- Maps tracking - Google maps
- Machine learning to ensure the project is enterprise production for better learnt
- Cluster fast way tracks
- Artificial Intelligence for the best method recommendation in taxi trip ways
- Navigating with prediction on the road with proper
    - Best price chosen
    - Best track on the road
- Get models to predict and embed
    - Machine learning models (Supervised learning ML models)
    - Deep learning models (Neural Network models)

## 🤖 Taxi Trip Project Construction Engine System
- Services are constructed reliable for engineering system as here as
    - Core ML
        • Feature engineering for data preprocessing to clear data missing
    - Business Logic
        • Ensure business logic toward to advantage cost management
    - Matching / Routing engine system
        • Route engine recommendation to answer the best road way trip chosen
    - Experimentation
        • A/B Testing inferences in otherway
    - Monitoring
        • Monitor models are using on production
- [Data Science]: Build Google Maps in a notebook cell Google maps display enterprise for taxi trip distance
    - Interactive map generated with 10 routes
    ![alt text](images/FE8C72D8-FB62-4205-8568-D82EA975BF00.png)
    - google maps previews
    ![alt text](images/A38D7ED6-0251-49E2-B116-63FD9E44A79E.png)
    - plot heatmap for maps traffic
    ![alt text](images/D2DDAEA0-BFC3-4ED8-966E-C536FC196278.png)
    - prediction with features on the trip
    ![alt text](images/02E9BFB2-8AF5-4708-A87B-DC5D1EAB08EC.png)
    - API Testing to ensure prediction is reliable
    ![alt text](images/E427ECCA-417B-48E3-B76A-28FEEF4D43A5.png)

- [Frontend]: Build UI Taxi apps for user (Production Grade)
     - UI display in website
        - Home display in website
        ![alt text](images/website/3BF3373D-7FE0-48A1-9036-4D7FE9214BB2.png)
        - Dashboard analytics
        ![alt text](images/website/3B6BC606-0169-4A59-9C23-49FEE4B82843.png)
        - Driver dashboard
        ![alt text](images/website/36E3104B-6614-448A-BF94-A0BCF06B6F3B.png)
        - Account trip service & payment method
        ![alt text](images/website/B59D7F33-AC71-40B5-BE1E-F7DAFD060B68.png)
    ------------------------------------------------------------
    - UI display in mobile appss
        - Home display in mobile apps
        ![alt text](images/mobile/4938600A-C313-4605-98C1-D9A0B9E1BA7E.png)
        - Pick up & drop location
        ![alt text](images/mobile/4938600A-C313-4605-98C1-D9A0B9E1BA7E.png)
        - Rides history
        ![alt text](images/mobile/3069ABDF-C67F-4F4F-8EE5-694D6B2A35F8.png)
        - Driver around tracking
        ![alt text](images/mobile/BA025216-8B62-4BB3-8B48-165E747F2D70.png)

- [Fullstack AI/ML Engineer]: Build MLOps Engineering system focused on AI/ML, Data Engineering to settle on the production, feature recommendation engineering
    - Target machine learning model
        - Predict Price
        - Predict completed at ride (timestamp for completing ride)
        - predict VTAT = Vehicle Time to Arrive (pickup time)
    - Docker containeraize dependencies system to run in wraps
    ![alt text](images/7BE01E65-69AD-4464-A8A1-98A2EA110103.png)
    - Create Database on PostgreSQL by occuring with docker
    ![alt text](images/1B2D32D4-C853-4CB5-B274-4CEC66A1C106.png)
    - Table rides as database in supabase
    ![alt text](images/A979B95D-3C85-4A3A-81C4-5ECE895E115C.png)
    - API integration based on database postgresql connection
        - Driver tracking for ride history
        ![alt text](images/261D920B-A831-4C0D-9444-951490A0C8B6.png)
        - LLM Chat answering question about routes in Jakarta
        ![alt text](images/1404721F-4232-43EF-90D0-04BE2E42F221.png)
    - Airflow for orchestration data ingesting    
        - SQL data ingestion by airflow monitoring in server
        ![alt text](images/416DC5F1-A4A6-4C1E-9676-6EF10812CC93.png)
        ![alt text](images/9ACD9AFD-17B7-4084-8F0F-7267D3CA13D9.png)
        - Airflow cluster activity to monitor data inference
        ![alt text](images/D8159409-6F3C-4E50-B08A-388B2AC6CE63.png)
    - Kafka to retrive data click button from customer

---

### **🚀 Complete Production Runbook**

```python
┌─────────────────────────────────────────┐
│  Frontend (React @ 4002)                │
├─────────────────────────────────────────┤
│  Backend (FastAPI @ 8000)               │
│  + Redis (cache @ 6379)                 │
│  + PostgreSQL (analytics @ 5433)        │
├─────────────────────────────────────────┤
│  Data Pipeline:                         │
│  • Airflow (scheduler @ 8080)           │
│  • Kafka (events @ 9092)                │
│  • Parquet files                        │
├─────────────────────────────────────────┤
│  Visualization:                         │
│  • Metabase (BI @ 3001)                 │
│  • Prometheus (metrics @ 9090)          │
│  • Grafana (dashboards @ 3000)          │
├─────────────────────────────────────────┤
│  Support:                               │
│  • MLflow (models @ 5001)               │
│  • Kafka-UI (@ 8081)                    │
│  • RedisInsight (@ 5540)                │
│  • Evidently-UI (LLM @ 8085)            │
└─────────────────────────────────────────┘
```

---

### **🔧 STEP 1: Verify Prerequisites**

bash

```python
# Check Docker
docker --version

# Check Docker Compose
docker-compose --version

# Verify you're in the right directory
cd /Users/miftahhadiyannoor/Documents/Gojek-Project
pwd

# Check .env file exists
ls -la production/.env
```

---

### **🔧 STEP 2: Verify .env Configuration**

```python
# View all critical environment variables
grep -E "POSTGRES_|AIRFLOW_|KAFKA_|REDIS_" production/.env | head -20

# Specific checks
grep POSTGRES_USER production/.env
grep POSTGRES_PASSWORD production/.env
grep POSTGRES_DB production/.env
grep KAFKA_BOOTSTRAP_SERVERS production/.env

Required variables to exist:

POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=gojek_taxi
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
AIRFLOW_DB_USER=airflow
AIRFLOW_DB_PASSWORD=airflow_password
```

---

### **🔧 STEP 3: Clean Up Old State**

```python
# List running containers
docker-compose ps

# Stop all services
docker-compose down

# Remove old volumes (CAREFUL - removes all data)
docker volume ls | grep gojek

# If you want fresh start:
docker-compose down -v

# Otherwise just down is fine

Expected output:
Stopping all running containers...
Removed all networks
```

**🔧 STEP 4: Build Docker Images**

```python
# Build backend image
docker-compose build --no-cache backend

# Build Airflow images
docker-compose build --no-cache airflow-webserver airflow-scheduler

# Check build succeeded
docker images | grep -E "gojek|backend|airflow"

Expected:
gojek-backend           latest    abc123...   900MB
gojek-airflow-webserver latest    def456...   2.5GB
```

**🔧 STEP 5: Start All Services (Ordered)**

**Phase 1: Infrastructure (2-3 minutes)**

```python
# Start databases first
docker-compose up -d postgres redis airflow-db

# Wait for databases to be healthy
sleep 5
docker-compose ps | grep -E "postgres|redis|airflow-db"
```

**Phase 2: Kafka & Coordination (2-3 minutes)**

```python
# Start Kafka ecosystem
docker-compose up -d zookeeper kafka

# Wait for Kafka to be healthy
sleep 10
docker-compose ps | grep -E "zookeeper|kafka"
```

**Phase 3: Middleware Services (2 minutes)**

```bash
# Start caching and tracking
docker-compose up -d mlflow redisinsight

# Start monitoring
docker-compose up -d prometheus

# Wait for all
sleep 5
docker-compose ps | grep -E "mlflow|redis|prometheus"
```

**Phase 4: Application Layer (3-5 minutes)**

```bash
# Start backend (depends on postgres, redis)
docker-compose up -d backend

# Wait for backend to be healthy (40+ seconds)
sleep 45
docker-compose ps backend

# Start frontend (depends on backend)
docker-compose up -d frontend

# Start Airflow (depends on airflow-db)
docker-compose up -d airflow-webserver airflow-scheduler

# Wait for all
sleep 10
```

**Phase 5: Visualization & Monitoring (2-3 minutes)**

```bash
# Start BI & monitoring tools
docker-compose up -d metabase grafana kafka-ui

# Start observability
docker-compose up -d evidently-ui

# Final wait
sleep 15
```

**Alternative: Start All at Once (Faster)**

```bash
# Start all services together
docker-compose up -d

# Monitor startup progress
docker-compose logs -f 2>&1 | head -100

# Wait for everything to stabilize (2-3 minutes)
sleep 120
```

**✅ STEP 6: Verify All Services Are Healthy**

```bash
# Show all services
docker-compose ps

# Count running services
docker-compose ps | grep "Up" | wc -l

# Should show: 15 services

Expected output - ALL should be "Up":
redis                Up (healthy)
redisinsight         Up
mlflow               Up (healthy)
postgres             Up (healthy)
backend              Up (healthy)
frontend             Up
metabase             Up (healthy)
prometheus           Up
grafana              Up
airflow-db           Up (healthy)
airflow-webserver    Up (healthy)
airflow-scheduler    Up
zookeeper            Up (healthy)
kafka                Up (healthy)
kafka-ui             Up
evidently-ui         Up (healthy)
```

**🔌 STEP 7: Test Each Service**

```bash
**Test Backend API**

# Check if API is responding
curl -X GET http://localhost:8000/health

# Should return JSON with status

Test PostgreSQL Connection
# Connect to database
docker exec postgres psql -U postgres -d gojek_taxi -c "SELECT version();"

# Should show PostgreSQL version

Test Redis
# Ping Redis
docker exec redis redis-cli ping

# Should return: PONG

Test Kafka
# List Kafka topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Should show: ride-requests, ride-events, driver-events, frontend-events

Test Airflow
# List DAGs
docker exec airflow_webserver airflow dags list

# Should show: rides_data_ingestion
```

**🌐 STEP 8: Access Web Interfaces**

| Service | URL | Purpose |
| --- | --- | --- |
| **Frontend** | http://localhost:4002 | React app |
| **Backend API** | http://localhost:8000/docs | Swagger UI |
| **Metabase** | http://localhost:3001 | BI Dashboard |
| **Grafana** | http://localhost:3000 | Monitoring (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics |
| **Airflow** | http://localhost:8080 | DAG Scheduler |
| **Kafka-UI** | http://localhost:8081 | Kafka Topics |
| **MLflow** | http://localhost:5001 | Model Tracking |
| **RedisInsight** | http://localhost:5540 | Redis UI |
| **Evidently** | http://localhost:8085 | LLM Monitoring |

**📊 STEP 9: Initialize Data Pipelines**

```bash
**Option A: Load Sample Data via Airflow**

# Trigger the data ingestion DAG
docker exec airflow_webserver airflow dags trigger rides_data_ingestion

# Monitor DAG run
docker exec airflow_webserver airflow dags list-runs --dag-id rides_data_ingestion

# View logs
docker-compose logs airflow_webserver | grep -i "extract\|load" | tail -20

---------------------------------------------------------------------------

Option B: Load Manually
# Insert sample data into PostgreSQL
docker exec backend python3 << 'EOF'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "postgres"),
    database=os.getenv("POSTGRES_DB", "gojek_taxi"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "password")
)
cursor = conn.cursor()

# Create sample rides
for i in range(100):
    cursor.execute("""
        INSERT INTO rides (ride_id, rider_id, driver_id, status, actual_fare)
        VALUES (%s, %s, %s, %s, %s)
    """, [f"ride_{i}", f"rider_{i%10}", f"driver_{i%5}", "completed", 50000 + i*1000])

conn.commit()
cursor.close()
conn.close()
print("✅ Inserted 100 sample rides")
EOF
```

**🔄 STEP 10: Configure Metabase (First Time)**

**Setup Metabase BI dashboard:**

1. **Open http://localhost:3001**
2. **Complete setup:**
    - Set admin email
    - Set admin password
    - Click "Let's get started"
3. **Connect to PostgreSQL:**
    - Click "Admin Settings" (gear icon)
    - Go to "Databases" → "New Database"
    - Database name: `taxi_analytics`
    - Database type: `PostgreSQL`
    - Host: `postgres`
    - Port: `5432`
    - Username: (from POSTGRES_USER in .env)
    - Password: (from POSTGRES_PASSWORD in .env)
    - Database: (from POSTGRES_DB in .env)
    - Click "Save"
4. **Create First Dashboard:**
    - Click "+" → "New dashboard"
    - Add cards/queries to visualize data
    - Save dashboard

## **📈 STEP 11: Monitor System Health**

**Check system metrics continuously:**

```bash
# Watch all container logs in real-time
docker-compose logs -f

# Or watch specific service
docker-compose logs -f backend

# Or watch errors only
docker-compose logs | grep -i error

# Check resource usage
docker stats

# Check disk usage
df -h
du -sh /var/lib/docker/volumes/*
```

**🚦 STEP 12: Common Operations**

```bash
Restart a Single Service

# Restart backend after code changes
docker-compose restart backend

# Wait for it to be healthy
sleep 10
docker-compose ps backend

Rebuild and Restart Backend
# After changing backend code
docker-compose build --no-cache backend
docker-compose up -d backend

View Service Logs
# Last 50 lines
docker-compose logs backend | tail -50

# Follow in real-time
docker-compose logs -f backend

# Filter for errors
docker-compose logs backend | grep -i error

Stop Everything
# Stop all services (data persists)
docker-compose down

# Stop all and remove volumes (WARNING: data lost)
docker-compose down -v
```

**✅ COMPLETE STARTUP SEQUENCE (Copy-Paste)**

```bash
# 1. Navigate to project
cd /Users/miftahhadiyannoor/Documents/Gojek-Project

# 2. Clean old state
docker-compose down

# 3. Build images
docker-compose build --no-cache backend airflow-webserver airflow-scheduler

# 4. Start infrastructure
docker-compose up -d postgres redis airflow-db zookeeper
sleep 15

# 5. Start Kafka
docker-compose up -d kafka
sleep 10

# 6. Start everything else
docker-compose up -d

# 7. Wait for all services
sleep 60

# 8. Verify all healthy
docker-compose ps

# 9. Test key services
curl http://localhost:8000/health
docker exec redis redis-cli ping
docker exec postgres psql -U postgres -d gojek_taxi -c "SELECT 1"

# 10. Open dashboards
echo "✅ Frontend: http://localhost:4002"
echo "✅ Backend API: http://localhost:8000/docs"
echo "✅ Metabase: http://localhost:3001"
echo "✅ Grafana: http://localhost:3000"
echo "✅ Airflow: http://localhost:8080"

Out of Disk Space
# Check Docker disk usage
docker system df

# Clean up unused volumes
docker volume prune

# Clean up unused images
docker image prune

Database Connection Error
# Test PostgreSQL directly
docker exec postgres psql -U postgres -c "SELECT version();"

# Check backend can reach postgres
docker exec backend ping postgres

# Check .env has correct credentials
grep POSTGRES production/.env

Port Already in Use
# Find what's using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port in docker-compose.yml
```

## **📋 EXPLANATION TABLE**

| Step | What It Does | Why | Time |
| --- | --- | --- | --- |
| 1. Verify prereqs | Checks Docker/Compose | Catch issues early | 30s |
| 2. Check .env | Loads configuration | Wrong config = broken services | 30s |
| 3. Clean up | Removes old containers/volumes | Fresh state, no conflicts | 1m |
| 4. Build images | Creates Docker images | Code packaged into containers | 3-5m |
| 5-6. Start infrastructure | Start postgres, redis, kafka | These are dependencies for other services | 2m |
| 7. Start all services | Start remaining 10 services | They depend on infrastructure | 2m |
| 8. Verify health | Checks all 15 services | Confirm everything started | 1m |
| 9. Test services | Test connectivity | Verify services are responding | 1m |
| 10. Access dashboards | Open web UIs | Verify visual interfaces work | 1m |