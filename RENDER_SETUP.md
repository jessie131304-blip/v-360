# Flipkart Voice360 — Render Ready

## Recommended deployment route

Render works best from a Git repository.

### Option A — GitHub + Render
1. Create a GitHub repository.
2. Upload all files from this ZIP to the repository root.
3. Go to render.com and sign in.
4. Click **New +** → **Web Service**.
5. Connect your GitHub repository.
6. Render should detect `render.yaml`, or configure manually:
   - Runtime: Python
   - Build Command: leave blank
   - Start Command: `python3 server.py`
7. Choose the free plan if available.
8. Deploy.
9. After deployment finishes, Render will give you a public `onrender.com` URL.

### Option B — Manual settings
If `render.yaml` is not detected:
- Environment / Runtime: Python
- Build Command: blank
- Start Command: `python3 server.py`
- Health Check Path: `/`

## Important

The app listens on `0.0.0.0` and automatically reads Render's `PORT`.

## Demo inputs

Normal / mixed:
The product is good but delivery was late and the package arrived damaged.

Sarcasm:
Amazing service. Only took them ten days to deliver.

Critical:
The phone is overheating and smells like burning while charging.

Multi-department:
The phone stopped working, delivery was late and customer support never responded.

## Persistence note

This academic prototype uses SQLite. On free ephemeral hosting, stored cases may reset when the service restarts/redeploys.
For the classroom demo, this is fine. If you need durable public persistence later, connect an external database.
