# 🚀 Live Deployment Guide

Follow these steps to get your **Smart Voting Live Link** for Mobile & PC.

## Option 1: Instant Demo (Ngrok)
This is the fastest way to get a real **HTTPS** link for testing on your phone today.
1. Download **ngrok** from [ngrok.com](https://ngrok.com/).
2. Open your terminal in the project folder.
3. Run: `ngrok http 5000`
4. Copy the `https://xxxx.ngrok-free.app` link.
5. Open this link on your mobile phone! 📱✨

## Option 2: Permanent Hosting (Render)
1. Push your project to **GitHub**.
2. Go to [Render.com](https://render.com/) and create a new **Web Service**.
3. Connect your GitHub repository.
4. Set the following:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. **Environment Secrets**:
   - Upload your `firebase_key.json` as a secret file.
   - Set `FIREBASE_ADMIN_CERT` to the path of the uploaded file.
6. Render will provide a permanent link like `https://smart-voting.onrender.com`.

## ⚠️ Important for Camera
Modern browsers will **BLOCK** the camera if you use an IP address (like `http://192.168...`). You **MUST** use a secure `https://` link (like the ones from Ngrok or Render) for the face scan to work on mobile.
