# DEPLOYMENT.md
> Nguyễn Tuấn Khải — Day 12: Deployment

## Thông tin Deploy

| | |
|---|---|
| **Student** | Nguyễn Tuấn Khải |
| **Platform** | Railway |
| **Service** | `06-lab-complete` |
| **Status** | ✅ Deployed |

## Public URL

```
Public URL:  https://day12-2a202600231-nguyentuankhai-production.up.railway.app
API Key:     dev-key-change-me-in-production
```

## Cách Deploy

```bash
cd 06-lab-complete

# Cài Railway CLI
npm i -g @railway/cli

# Login
railway login

# Init project
railway init

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set AGENT_API_KEY=my-secret-key-change-me
railway variables set JWT_SECRET=my-jwt-secret-change-me
railway variables set PORT=8000

# Deploy
railway up

# Lấy public URL
railway domain
```

## Test Public URL

```bash
PUBLIC_URL="<url từ railway domain>"
API_KEY="my-secret-key-change-me"

# Health check
curl $PUBLIC_URL/health

# Readiness check
curl $PUBLIC_URL/ready

# Ask endpoint
curl -X POST $PUBLIC_URL/ask \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
```

## Chạy Grading Script

```bash
cd e:\a\codeLabAI\Day12-2A202600231-NguyenTuanKhai

python grand-my-lab.py ./06-lab-complete $PUBLIC_URL $API_KEY
```

## Kết quả Grading

```
============================================================
🧪 STARTING AUTOMATED GRADING FOR DAY 12 LAB
Target URL: https://day12-2a202600231-nguyentuankhai-production.up.railway.app
============================================================
✅ Dockerfile exists: 2/2
✅ docker-compose.yml exists: 2/2
✅ requirements.txt exists: 1/1
✅ Multi-stage Dockerfile: 5/5
✅ Docker Compose setup: 4/4
✅ No hardcoded secrets: 5/5
✅ Authentication required: 5/5
✅ Authentication functional: 5/5
✅ Rate limiting (Ex 4.3): 5/5
✅ Health check endpoint: 3/3
✅ Readiness check endpoint: 3/3
✅ Conversation history (Stateless): 10/10
✅ Public deployment works: 10/10
============================================================
🎯 AUTOMATED SCORE: 60/60
📈 PERCENTAGE: 100.0%
============================================================
💡 Total Estimated Grade: ~100/100
```
