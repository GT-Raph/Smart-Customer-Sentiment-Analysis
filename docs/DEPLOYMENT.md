# Self-hosted deployment

## XAMPP setup

Start MySQL from the XAMPP Control Panel. In phpMyAdmin, open the SQL tab and run:

```sql
CREATE DATABASE smart_sentiment
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sentiment_app'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON smart_sentiment.* TO 'sentiment_app'@'localhost';
FLUSH PRIVILEGES;
```

Copy `.env.example` to `.env`, set the same MySQL password and a random Django
secret, then initialize the schema and administrator:

```powershell
cd emotion_dashboard
py manage.py migrate
py manage.py createsuperuser
```

Open `http://localhost:8000/admin/`, sign in, and create at least one Branch.
Then create a key for each camera, using the branch ID shown in Django admin:

```powershell
py manage.py create_device_key --branch 1 --name front-desk-camera --pc-name ACCRA01-CAMERA
```

Copy the printed key immediately into `DEVICE_API_KEY` on that camera computer.
It cannot be displayed again. Set `INGESTION_API_URL` to the API address and run:

```bash
python clients/device_agent.py
```

The dashboard is served on port 8000 and the ingestion API on port 8001.
The API and worker read the same `MYSQL_*` settings as Django, so all services
share the XAMPP database. Redis is still required for the background queue.

Docker Compose can run Redis and the Python services while XAMPP runs on the
Windows host. For that mode, create an application database account permitted to
connect from Docker and keep the Compose override `MYSQL_HOST=host.docker.internal`.

## Production checklist

- Set `DJANGO_DEBUG=false` and configure real hosts, trusted origins, and HTTPS.
- Restrict ports 3306 and 6379 to trusted local clients.
- Use strong, unique database and Django secrets.
- Back up the XAMPP MariaDB database and test restoration regularly.
- Configure centralized logs, monitoring, and error reporting.
- Use private object storage if services run on more than one host.
- Review consent, retention, and biometric-data requirements for your jurisdiction.
