# Guide: Deploying Smart Voting to .web.app 🌎🚀

To get your project live on a `web.app` domain, we will use **Google Cloud Run** (to host the Python code) and **Firebase Hosting** (to get the official domain).

## Prerequisites
1.  **Google Cloud Project**: Create one at [console.cloud.google.com](https://console.cloud.google.com).
2.  **Firebase Project**: Link it to your Google Cloud project at [console.firebase.google.com](https://console.firebase.google.com).
3.  **Google Cloud CLI (gcloud)**: Installed on your PC.

---

## Step 1: Build & Deploy to Cloud Run
Run these commands in your project folder:
```bash
# 1. Enable needed services
gcloud services enable run.googleapis.com containerregistry.googleapis.com

# 2. Build and Push the Docker image
gcloud builds submit --tag gcr.io/[PROJECT_ID]/smart-voting-app

# 3. Deploy to Cloud Run (Choose us-central1)
gcloud run deploy smart-voting-app \
  --image gcr.io/[PROJECT_ID]/smart-voting-app \
  --platform managed \
  --allow-unauthenticated \
  --region us-central1
```

## Step 2: Link to Firebase Hosting
1.  Install Firebase Tools: `npm install -g firebase-tools`.
2.  Log in: `firebase login`.
3.  Initialize: `firebase init hosting`.
    - Select your project.
    - Public directory: `public`.
    - Configure as single-page app: `Yes`.
4.  **Important**: I have already created the [firebase.json](file:///d:/Softwares/smart%20voting/firebase.json) file for you. It maps all requests to your Cloud Run service.
5.  **Deploy**: `firebase deploy --only hosting`.

## Step 3: Use your .web.app Link
Firebase will provide you with a link like:
`https://[PROJECT-ID].web.app`

---

## Why this approach?
- **Python Support**: Firebase Hosting only hosts static files, but linking it to Cloud Run (via the `rewrites` in `firebase.json`) allows you to run your full Python Flask app on the `web.app` domain.
- **Custom Domain**: You can now easily add your own `.com` or `.org` later!
