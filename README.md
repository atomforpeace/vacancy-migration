# vacancy-migration

# upload.sh
#!/bin/bash

cd vacancy-migration/
git pull
pip3 install -r requirements.txt
cd vacancy
python3 manage.py migrate
sudo systemctl restart gunicorn
sudo systemctl restart nginx
exit 0

# nginx
server {
    listen 80;
    server_name <server_ip>;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /home/<user_name>/vacancy-migration/vacancy-migration/vacancy;
    }

    location /media/ {
        root /home/<user_name>/vacancy-migration/vacancy-migration/vacancy;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}

# nginx + gunicorn
https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-18-04-ru

# psycopg trouble
https://stackoverflow.com/questions/5420789/how-to-install-psycopg2-with-pip-on-python
