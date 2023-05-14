git fetch
git pull
docker compose -f ./docker-compose.base.yml -f ./docker-compose.traefik.yml up --build
