# Deployment Guide: National Weather Big Data Analytics Platform (VayuDrishti)

This guide covers 4 production deployment methods:
1. [One-Click Cloud (Render / Railway / Fly.io)](#option-1-free--easy-cloud-deployment-render--railway) (Recommended for quick public demo)
2. [Docker & Docker Compose](#option-2-docker--docker-compose-production)
3. [Linux VPS / AWS EC2 / DigitalOcean (systemd + Nginx)](#option-3-linux-vps--aws-ec2-with-systemd--nginx)
4. [Instant Public URL via Cloudflare Tunnel / Ngrok](#option-4-instant-public-tunnel-from-local-machine)

---

## Option 1: Free & Easy Cloud Deployment (Render / Railway)

### Deploying on Render (Free)
1. Push your code to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of VayuDrishti Platform"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/vayudrishti.git
   git push -u origin main
   ```
2. Go to [render.com](https://render.com) and create an account.
3. Click **New +** $\rightarrow$ **Web Service**.
4. Connect your GitHub repository.
5. Set:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt websockets`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
6. Click **Deploy Web Service**. You will receive an active HTTPS URL (e.g. `https://vayudrishti.onrender.com`).

### Deploying on Railway
1. Go to [railway.app](https://railway.app) $\rightarrow$ **New Project** $\rightarrow$ **Deploy from GitHub repo**.
2. Railway automatically detects the `Procfile` and `requirements.txt` and deploys the platform with a public domain.

---

## Option 2: Docker & Docker Compose (Production)

### Quick Start with Docker Compose
Run in the project directory:
```bash
docker-compose up -d --build
```

- Open `http://localhost:8080` in your browser.
- Check logs: `docker-compose logs -f`
- Stop container: `docker-compose down`

### Build & Run Docker Image Directly
```bash
# Build image
docker build -t vayudrishti-platform .

# Run container on port 8080
docker run -d --name vayudrishti -p 8080:8080 vayudrishti-platform
```

---

## Option 3: Linux VPS / AWS EC2 with systemd + Nginx

### 1. Server Setup
SSH into your Ubuntu/Debian server:
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx git
git clone https://github.com/YOUR_USERNAME/vayudrishti.git /var/www/vayudrishti
cd /var/www/vayudrishti

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt websockets gunicorn
```

### 2. Create Systemd Service
Create `/etc/systemd/system/vayudrishti.service`:
```ini
[Unit]
Description=VayuDrishti Weather Big Data Platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/vayudrishti
Environment="PATH=/var/www/vayudrishti/venv/bin"
ExecStart=/var/www/vayudrishti/venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vayudrishti
sudo systemctl start vayudrishti
```

### 3. Nginx Reverse Proxy & SSL
Configure `/etc/nginx/sites-available/vayudrishti`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site and install free SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/vayudrishti /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Option 4: Instant Public Tunnel from Local Machine

If you want to expose your locally running instance publicly for demos or team sharing:

### Using Cloudflare Tunnels (Zero Install / Instant HTTPS):
```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

### Using Ngrok:
```bash
ngrok http 8080
```
This gives you an instant, secure public `https://...` link that connects directly to your live platform and WebSocket feed.
