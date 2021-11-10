#!/bin/bash

trap "echo script failed; exit 1" ERR
read -s -r -p "Password to use for accounts: " user_passwd
echo
read -s -r -p "Github API token: " github_token
echo
read -r -p "Github username: " github_username
echo
read -r -p "Orchestrator IP address: " orchestrator_ip
echo

# install general packages
cd ~ || exit
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install apt-utils -y
sudo apt-get install build-essential git screen htop ncdu -y
sudo apt-get install python3-dev python3-venv python3-pip python3-wheel -y

# install MariaDB
sudo apt-get install mariadb-server -y
sudo apt-get install expect -y

SECURE_MYSQL=$(sudo expect -c "
set timeout 10
spawn mysql_secure_installation
expect \"Enter current password for root (enter for none):\"
send \"\r\"
expect \"Set root password?\"
send \"n\r\"
expect \"Remove anonymous users?\"
send \"y\r\"
expect \"Disallow root login remotely?\"
send \"y\r\"
expect \"Remove test database and access to it?\"
send \"y\r\"
expect \"Reload privilege tables now?\"
send \"y\r\"
expect eof
")
echo "$SECURE_MYSQL"

sudo apt-get purge expect -y

sudo mysql -e "GRANT ALL ON *.* TO 'gamemaster '@'localhost' IDENTIFIED BY '$user_passwd' WITH GRANT OPTION;"
sudo mysql -e "FLUSH PRIVILEGES;"
sudo mysql -e "DROP SCHEMA IF EXISTS diamant;"
sudo mysql -e "CREATE SCHEMA diamant;"

# install docker
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y

# prepare docker
for cid in $(sudo docker ps -a -q)
do
  sudo docker stop "$cid"
  sudo docker rm "$cid"
done


echo "$github_token" | sudo docker secret create GITHUB_API_TOKEN -
echo "$github_username" | sudo docker secret create GITHUB_USERNAME -
echo "$user_passwd" | sudo docker secret create USER_PASSWORD -


sudo docker run --restart always -d -p 5672:5672 rabbitmq

sudo docker swarm leave --force 2>/dev/null || echo
SWARM_INIT_OUT=$(sudo docker swarm init --advertise-addr "$orchestrator_ip" --default-addr-pool 10.4.0.0/16 | grep "docker swarm join --token")
sudo docker node update --label-add registry=true "$(sudo docker node ls --filter "role=manager" --format '{{.ID}}')"

sudo docker service create \
  --name registry \
  --constraint 'node.labels.registry==true' \
  --mount source=registry_data,target=/var/lib/registry \
  -e REGISTRY_HTTP_ADDR=0.0.0.0:5000 \
  --publish published=5000,target=5000 \
  --replicas 1 \
  registry:2

# deprecated with https://github.com/ucl-cs-diamant/docker/commit/397f251f29ea3c92d4dcff7dfafcc16c41407a53
# sudo docker build https://github.com/ucl-cs-diamant/docker.git#:ubuntu-gamerunner -t ubuntu-gamerunner

sudo docker build https://github.com/ucl-cs-diamant/docker.git -t gamerunner
sudo docker tag gamerunner localhost:5000/gamerunner
sudo docker push localhost:5000/gamerunner

sudo docker service create --detach -e GAMESERVER_HOST="$orchestrator_ip" -e GAMESERVER_PORT=8000 --replicas 12 --name gamerunner_service localhost:5000/gamerunner



setup_backend() {
  # clone and run backend
  cd ~ && rm -rf diamant-backend
  cd ~ && git clone https://github.com/ucl-cs-diamant/diamant-backend
  cd diamant-backend || exit
  printf "GITHUB_API_TOKEN=%s
GITHUB_API_TOKEN_USER=%s
MATCH_TIMEOUT=15
PLAYER_DECISION_TIMEOUT=1\n" "$github_token" "$github_username" >.env

  printf "[client]
host = localhost
database = diamant
user = gamemaster
password = %s
default-character-set = utf8\n" "$user_passwd" >mariadb.cnf

  sudo apt-get install default-libmysqlclient-dev -y
  python3 -m venv venv
  source venv/bin/activate
  python3 -m pip install wheel
  python3 -m pip install -r requirements.txt
  python3 manage.py migrate
  deactivate

  pkill screen || echo "No screen to kill"
  screen -AdmS diamant_servers -t placeholder_window
  screen -S diamant_servers -x -X screen -t django bash -c "source venv/bin/activate && python3 manage.py runserver 0.0.0.0:8000"
  screen -S diamant_servers -x -X screen -t celery bash -c "source venv/bin/activate && python3 -m celery -A Diamant worker -l INFO"
  screen -S diamant_servers -x -X screen -t celerybeat bash -c "source venv/bin/activate && python3 -m celery -A Diamant beat -l INFO"
}


continue_running="placeholder"
while true; do
  if [[ -n "$continue_running" ]]; then
    case "$continue_running" in [yY])
      echo "Setting up backend..."
      setup_backend
      break
      ;;
    [nN])
      break
      ;;
    *)
      read -t 120 -r -p "Continue and set up backend servers? [Y/n] " continue_running || (
        echo
        continue_running="Y"
      )
      ;;
    esac
  fi
done


echo "All done."
echo "To join the swarm as a worker node, use the following worker join string: "
echo "${SWARM_INIT_OUT#*--token}"
echo "${SWARM_INIT_OUT#*--token}" > worker_join_string
