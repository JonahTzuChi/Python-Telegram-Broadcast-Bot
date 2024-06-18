docker-compose up --build --no-start

master_tag=master_latest
worker_tag=worker_latest

docker tag src-master_bot:latest jonahyeoh/python-telegram-broadcast-bot:${master_tag}
docker push jonahyeoh/python-telegram-broadcast-bot:${master_tag}

docker tag src-worker_bot:latest jonahyeoh/python-telegram-broadcast-bot:${worker_tag}
docker push jonahyeoh/python-telegram-broadcast-bot:${worker_tag}

# Achieve Supply chain attestations
# cd to folder with Dockerfile and call command below
# remember to update tagname!!!
# docker buildx build --provenance=true --sbom=true -t jonahyeoh/python-telegram-broadcast-bot:tagname --push .