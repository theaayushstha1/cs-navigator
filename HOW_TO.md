# CS Navigator - Quick Reference

## Local Development

### Start Frontend
```bash
cd frontend
npm install      # first time only
npm run dev      # starts on http://localhost:5173
```

### Start Backend
```bash
cd backend
python -m venv .venv          # first time only
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt   # first time only
uvicorn main:app --reload --port 8000
```

---

## Deploy to AWS

### One Command Deploy
```bash
bash deploy.sh
```

### Access EC2
```bash
ssh -i "your-key.pem" ubuntu@18.214.136.155
```

### On EC2 - Check Services
```bash
cd ~/cs-chatbot-morganstate
docker-compose ps          # check status
docker-compose logs -f     # view logs
docker-compose restart     # restart services
```

---

## Initial Setup (First Time)

### 1. Clone Repo
```bash
git clone https://github.com/YOUR_USERNAME/cs-chatbot-morganstate.git
cd cs-chatbot-morganstate
```

### 2. Create Backend `.env`
```bash
# backend/.env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=csnavigator
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
JWT_SECRET=your-secret-key
```

### 3. Create Frontend `.env`
```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

### 4. PEM Key (for EC2)
- Download from AWS Console → EC2 → Key Pairs
- Save as `your-key.pem`
- Set permissions: `chmod 400 your-key.pem`

---

## Useful Commands

| Task | Command |
|------|---------|
| Kill port 8000 | `npx kill-port 8000` |
| Build frontend | `cd frontend && npm run build` |
| Check Python version | `python --version` |
| View backend logs | `docker-compose logs backend` |
| Restart containers | `docker-compose restart` |

---

*Last updated: January 2026*
