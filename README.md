
An AI-powered Retrieval-Augmented Generation (RAG) chatbot designed to assist students in the Morgan State University Computer Science Department.

#  Chatbot App (Frontend + Backend + MySQL)

This is a full-stack chatbot application that runs entirely in Docker using Docker Compose.  
It includes:

- Backend (API server)
- Frontend (User interface)
- MySQL Database

All images are pre-built and stored privately on Docker Hub.

---


This folder contains everything you need:

- `docker-compose.yml` – defines how to run the app
- `backend/.env.example` – shows the environment variable format
- `README.md` – this guide

---

##Prerequisites

- Docker installed: [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
- Docker Hub account (free)
- You’ve been added as a collaborator to this private Docker Hub repo: `sakina593/chatbot`

---

## Step 1: Log in to Docker Hub

```bash
docker login


Step 2: Create .env File

Copy and rename the example file:
cp backend/.env.example backend/.env


Step 3: Run the App
From the folder with docker-compose.yml, run:

docker compose up



##########github
Anytime you add or edit code, you just follow these three steps in your project folder:

1. Stage changes
git add .

(If you want to stage only one file, replace . with the filename, e.g. git add backend/main.py.)

2. Commit changes
git commit -m "Your short message about the changes"


3. Push to GitHub
git push


=======
# MSU CS navigator
It is an AI-powered Retrieval-Augmented Generation (RAG) chatbot designed to assist students in the Morgan State University Computer Science Department.
>>>>>>> 14a35ba989553c5e77497e85a27e8df7e9c272bc
