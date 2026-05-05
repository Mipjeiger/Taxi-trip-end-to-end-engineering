1. access PostgreSQL

Option 1: Access via Docker Exec (Inside the Container)
    docker exec -it taxi_trip_db psql -U postgres -d taxi_trip_db

Option 2: Access via Local Terminal (Outside the Container)
    psql -h localhost -p 5432 -U postgres -d taxi_trip_db

----------------------------------------------

🧪 Test Local Build First (Before Docker)

bash
cd production/frontend

# Clean install
rm -rf node_modules package-lock.json
npm install

# Test build locally
npm run build

# If build succeeds, Docker will work
ls -la build/  # Should show built files