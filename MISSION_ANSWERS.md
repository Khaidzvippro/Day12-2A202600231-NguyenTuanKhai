# MISSION_ANSWERS.md
> Nguyễn Tuấn Khải — Day 12: Deployment

---

## Part 1: Localhost vs Production

### Exercise 1.1 — 5 Anti-patterns trong `develop/app.py`

| # | Vấn đề | Dòng code | Hậu quả |
|---|--------|-----------|---------|
| 1 | **Hardcode API key & DB URL** | `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` | Lộ secret khi push lên GitHub |
| 2 | **Log ra secret** | `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` | Secret bị ghi vào log, ai cũng đọc được |
| 3 | **Không có `/health` endpoint** | Không tồn tại | Platform không biết container crash để restart |
| 4 | **`host="localhost"` cố định** | `uvicorn.run(..., host="localhost")` | Container không nhận được request từ bên ngoài |
| 5 | **`reload=True` và `DEBUG=True` cứng** | `reload=True` | Tốn tài nguyên, rủi ro bảo mật trên production |

### Exercise 1.2 — Chạy basic version

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py

# Test
curl -X POST "http://localhost:8000/ask?question=hello"
# => {"answer": "Tôi là AI agent được deploy lên cloud..."}
```

Quan sát terminal thấy secret bị in ra:
```
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
```

### Exercise 1.3 — Bảng so sánh develop vs production

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
|---------|----------------|----------------------|---------------------|
| Config | Hardcode trong code | `os.getenv()` qua `config.py` | Thay đổi config không cần sửa code, không lộ secret |
| Health check | Không có | `/health` + `/ready` | Platform biết khi nào restart container |
| Logging | `print()` + log secret | Structured JSON, không log secret | Dễ parse bằng log aggregator, an toàn |
| Shutdown | Đột ngột (không xử lý) | Graceful (SIGTERM handler) | Không mất request đang xử lý khi tắt |
| Host binding | `localhost` | `0.0.0.0` | Container nhận được request từ bên ngoài |
| Port | Cứng `8000` | Đọc từ `PORT` env var | Railway/Render inject PORT tự động |

---

## Part 2: Docker Containerization

### Exercise 2.1 — Câu hỏi về Dockerfile (develop)

**1. Base image là gì?**
`python:3.11` — full Python distribution, khoảng ~1GB.

**2. Working directory là gì?**
`/app` — được set bằng lệnh `WORKDIR /app`.

**3. Tại sao COPY requirements.txt trước?**
Docker build theo từng layer và cache lại. Nếu `requirements.txt` không thay đổi, Docker dùng cache layer cũ — không cần `pip install` lại, build nhanh hơn nhiều.

**4. CMD vs ENTRYPOINT khác nhau thế nào?**
- `CMD`: lệnh mặc định, có thể override khi `docker run`
- `ENTRYPOINT`: lệnh cố định, không bị override; dùng khi muốn container luôn chạy một binary cụ thể

### Exercise 2.2 — Build và run develop

```bash
cd e:\a\codeLabAI\Day12-2A202600231-NguyenTuanKhai

docker build -f 02-docker/develop/Dockerfile -t agent-develop .
docker run -p 8000:8000 agent-develop
docker images agent-develop
```

Image `agent-develop` dùng `python:3.11` full → size ~**1GB+**.

### Exercise 2.3 — Multi-stage build (production)

**Stage 1 (builder):** Cài `gcc`, `libpq-dev`, build wheel cho tất cả dependencies. Image này dùng để compile, không deploy.

**Stage 2 (runtime):** Chỉ copy wheel đã build từ Stage 1 sang image `python:3.11-slim` sạch. Không có build tools, không có compiler.

**Tại sao image nhỏ hơn?**
Stage 2 chỉ chứa Python slim + packages đã compile, không có gcc, build cache, hay các tool không cần thiết → giảm từ ~1GB xuống còn ~200–300MB.

```bash
docker build -f 02-docker/production/Dockerfile -t agent-production .
docker images | grep agent
# agent-develop    ~1.06GB
# agent-production ~280MB
```

### Exercise 2.4 — Sơ đồ kiến trúc Docker Compose (production)

```
Internet
    │
    ▼
┌─────────────────────┐
│  Nginx :80 / :443   │  ← Reverse proxy, rate limit, security headers
└────────┬────────────┘
         │ proxy_pass (round-robin)
         ▼
┌─────────────────────┐
│  Agent (FastAPI)    │  ← Business logic, auth, LLM call
│  port 8000          │
└────────┬────────────┘
         │
   ┌─────┴──────┐
   ▼            ▼
┌──────┐  ┌──────────┐
│Redis │  │  Qdrant  │
│:6379 │  │  :6333   │
└──────┘  └──────────┘
 Cache &    Vector DB
 Sessions   (RAG)
```

Services trong `docker-compose.yml`: **agent**, **redis**, **qdrant**, **nginx** — tất cả trong network `internal`.

---

## Part 3: Cloud Deployment

### Exercise 3.1 — Deploy Railway

```bash
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key
railway up
railway domain
```

### Exercise 3.2 — So sánh `render.yaml` vs `railway.toml`

| | `railway.toml` | `render.yaml` |
|---|---|---|
| Format | TOML | YAML |
| Build command | `[build] builder = "DOCKERFILE"` | `buildCommand` field |
| Health check | Không cần khai báo | `healthCheckPath` |
| Env vars | Set qua CLI | Set qua Dashboard hoặc file |
| Auto-deploy | Khi `railway up` | Khi push lên GitHub |

---

## Part 4: API Security

### Exercise 4.1 — API Key Authentication

**API key được check ở đâu?**
Trong FastAPI Dependency qua header `X-API-Key`. Nếu key sai → trả về `401 Unauthorized`.

**Làm sao rotate key?**
Thay giá trị `AGENT_API_KEY` trong environment variable, restart service — không cần deploy lại code.

```bash
# Không có key → 401
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

# Có key → 200
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

### Exercise 4.2 — JWT Authentication

JWT flow:
1. Client POST `/token` với username/password → nhận JWT token (có expiry 60 phút)
2. Client gửi mọi request tiếp theo với header `Authorization: Bearer <token>`
3. Server verify signature + expiry, extract `user_id` và `role` từ payload
4. Không cần lookup database mỗi request — stateless

### Exercise 4.3 — Rate Limiting

**Algorithm:** Sliding window counter — đếm số request trong 60 giây qua.

**Limit:** 10 req/min cho user thường, 100 req/min cho admin.

**Bypass cho admin:** Kiểm tra `role` trong JWT payload, nếu là `admin` thì dùng limit cao hơn.

```bash
# Gọi 20 lần liên tiếp → request thứ 11+ nhận 429
for i in {1..20}; do
  curl -X POST http://localhost:8000/ask \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}'
done
```

### Exercise 4.4 — Cost Guard Implementation

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng tự động (TTL 32 ngày)
    """
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days TTL
    return True
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1 — Health Checks

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": settings.app_version,
    }

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic chưa?"""
    try:
        r.ping()  # Check Redis
        return {"ready": True}
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")
```

**Sự khác biệt:**
- `/health` → "container còn sống không?" — platform dùng để quyết định có restart không
- `/ready` → "có sẵn sàng nhận traffic không?" — load balancer dùng để route request

### Exercise 5.2 — Graceful Shutdown

```python
import signal

def shutdown_handler(signum, frame):
    """Handle SIGTERM — platform gửi signal này khi muốn dừng container."""
    logger.info("SIGTERM received — finishing in-flight requests...")
    # 1. Stop accepting new requests (uvicorn tự xử lý)
    # 2. Hoàn thành requests đang chạy
    # 3. Đóng Redis connection
    # 4. Exit

signal.signal(signal.SIGTERM, shutdown_handler)
```

Test:
```bash
python app.py &
PID=$!
curl http://localhost:8000/ask -X POST -d '{"question": "Long task"}' &
kill -TERM $PID
# Quan sát: request hoàn thành trước khi process exit
```

### Exercise 5.3 — Stateless Design

**Anti-pattern (in-memory):**
```python
conversation_history = {}  # Mỗi instance có dict riêng → scale ra 3 instance là mất data

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
```

**Correct (Redis):**
```python
@app.post("/ask")
def ask(user_id: str, question: str):
    history = r.lrange(f"history:{user_id}", 0, -1)  # Tất cả instance đọc cùng 1 Redis
    r.rpush(f"history:{user_id}", question)
    r.expire(f"history:{user_id}", 3600)
```

**Tại sao quan trọng?** Khi scale lên 3 instances, mỗi request có thể vào instance khác nhau. Nếu state lưu trong memory của instance A, instance B không có → conversation bị mất.

### Exercise 5.4 — Load Balancing

```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3

# Test phân tán traffic
for i in {1..10}; do
  curl http://localhost:8080/ask -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Request '$i'"}'
done

# Xem served_by trong response — sẽ thấy nhiều instance khác nhau
docker compose logs agent
```

Nginx round-robin phân đều request sang 3 instances. Nếu 1 instance die, Nginx tự chuyển traffic sang 2 instance còn lại.
