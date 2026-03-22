# 100% Free Deployment Guide: Render.com 🚀

Since you want a completely free deployment without entering a credit card, the industry standard is **Render.com**. It will give you a professional, permanent domain like `https://smart-voting.onrender.com`.

This is the standard flow used by developers everywhere to get free hosting.

---

## **Step 1: Put your Code on GitHub (Free)**
Render pulls your code directly from GitHub to host it.
1. Go to [GitHub.com](https://github.com) and create a free account if you don't have one.
2. In the top right, click the **+** icon and select **New repository**.
3. Name it `smart-voting-system`. Make sure it is set to **Public** or **Private**.
4. Click **Create repository**.
5. Keep that page open; it has some commands you'll need.

## **Step 2: Upload your code from your PC to GitHub**
You need `Git` installed on your computer. If you don't have it, download and install it from [git-scm.com](https://git-scm.com/).
1. Open PowerShell (or Terminal) in your `:\dSoftwares\smart voting` folder.
2. Run these commands one by one:
```powershell
git init
git add .
git commit -m "First upload"
git branch -M main
```
3. Look at your GitHub page, copy the command that looks like `git remote add origin https://github.com/YourName/smart-voting-system.git`, and run it.
4. Finally, run:
```powershell
git push -u origin main
```
*Your code is now safe on the internet!*

## **Step 3: Deploy to Render for Free**
1. Go to [Render.com](https://render.com) and sign up for a free account (you can just click "Sign up with GitHub").
2. Once logged in, click **New +** and select **Web Service**.
3. Click **Build and deploy from a Git repository**.
4. You will see a list of your GitHub repositories. Click **Connect** next to `smart-voting-system`.
5. Fill out the form:
   - **Name**: `smart-voting` (This will be your URL: `smart-voting.onrender.com`)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free
6. Click **Create Web Service**.

## 🎉 **Done!**
Render will now read your `render.yaml` file and build your application. In about 5 minutes, your Smart Voting System will be live on the internet, 24/7, for absolutely free!
