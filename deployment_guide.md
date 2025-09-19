# Production Deployment Configuration
# Choose one of these platforms:

# === HEROKU (Easiest) ===
# 1. Create Procfile:
# web: python web_app.py --port=$PORT --host=0.0.0.0

# 2. Create runtime.txt:
# python-3.9.18

# 3. Update web_app.py for Heroku:
# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port, debug=False)

# === RAILWAY (Modern Alternative) ===
# 1. Connect GitHub repo
# 2. Auto-deploys on push
# 3. Free tier: 500 hours/month

# === RENDER (Free Tier) ===
# 1. Connect repo
# 2. Build command: pip install -r requirements.txt  
# 3. Start command: python web_app.py

# === DOCKER (Universal) ===
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "web_app.py", "--host=0.0.0.0", "--port=5000"]

# Build: docker build -t trading-app .
# Run: docker run -p 5000:5000 trading-app