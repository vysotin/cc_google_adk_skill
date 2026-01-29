# Production Deployment

## Table of Contents
- [Vertex AI Agent Engine](#vertex-ai-agent-engine)
- [Cloud Run](#cloud-run)
- [Google Kubernetes Engine](#google-kubernetes-engine)
- [Docker/Container](#dockercontainer)
- [Configuration Management](#configuration-management)
- [Monitoring and Observability](#monitoring-and-observability)
- [Production Checklist](#production-checklist)

## Vertex AI Agent Engine

Google's recommended managed platform for ADK agents. Auto-scaling, built-in monitoring.

### Deploy

```bash
# Authenticate
gcloud auth application-default login

# Deploy agent
gcloud agent-engine deploy my_agent \
  --project=my-project \
  --region=us-central1

# With custom config
gcloud agent-engine deploy my_agent \
  --config=agent-config.yaml \
  --memory=2Gi \
  --cpu=2
```

### agent-config.yaml

```yaml
runtime:
  python_version: "3.11"

resources:
  memory: "2Gi"
  cpu: "2"

scaling:
  min_instances: 1
  max_instances: 10

environment:
  GOOGLE_API_KEY: ${GOOGLE_API_KEY}
  LOG_LEVEL: INFO

session_service:
  type: firestore
  database: agent-sessions

memory_service:
  type: vertex_ai_search
  datastore_id: agent-memory
```

### Programmatic Deployment

```python
from google.cloud import aiplatform

aiplatform.init(project="my-project", location="us-central1")

# Deploy
endpoint = aiplatform.AgentEndpoint.deploy(
    agent_dir="./my_agent",
    machine_type="n1-standard-2",
    min_replica_count=1,
    max_replica_count=10
)

# Invoke
response = endpoint.predict(
    user_id="user123",
    session_id="session456",
    message="Hello"
)
```

## Cloud Run

Containerized deployment with serverless scaling.

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
```

### main.py

```python
from flask import Flask, request, jsonify
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from my_agent import root_agent
import os

app = Flask(__name__)
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="cloud-run-agent", session_service=session_service)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    new_message = types.Content(
        role="user", parts=[types.Part(text=data["message"])]
    )
    results = []
    for event in runner.run(
        user_id=data["user_id"],
        session_id=data["session_id"],
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    results.append({"type": "content", "text": part.text})
    return jsonify({"events": results})

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

### Deploy

```bash
# Build and deploy
gcloud run deploy my-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_API_KEY=${GOOGLE_API_KEY}"

# With Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

### cloudbuild.yaml

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/my-agent', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/my-agent']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'my-agent'
      - '--image'
      - 'gcr.io/$PROJECT_ID/my-agent'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'

images:
  - 'gcr.io/$PROJECT_ID/my-agent'
```

## Google Kubernetes Engine

Full control with Kubernetes orchestration.

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adk-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: adk-agent
  template:
    metadata:
      labels:
        app: adk-agent
    spec:
      containers:
        - name: agent
          image: gcr.io/my-project/my-agent:latest
          ports:
            - containerPort: 8080
          env:
            - name: GOOGLE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: agent-secrets
                  key: google-api-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: adk-agent-service
spec:
  selector:
    app: adk-agent
  ports:
    - port: 80
      targetPort: 8080
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: adk-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: adk-agent
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Deploy

```bash
# Create cluster
gcloud container clusters create adk-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-2 \
  --region=us-central1

# Deploy
kubectl apply -f deployment.yaml

# Create secret
kubectl create secret generic agent-secrets \
  --from-literal=google-api-key=${GOOGLE_API_KEY}
```

## Docker/Container

For offline or custom environments.

### docker-compose.yaml

```yaml
version: '3.8'
services:
  agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - SESSION_BACKEND=redis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Run

```bash
docker-compose up -d
```

## Configuration Management

### Environment Variables

```python
import os
from google.adk.agents import Agent

agent = Agent(
    name="production_agent",
    model=os.getenv("MODEL_ID", "gemini-2.0-flash"),
    instruction=os.getenv("AGENT_INSTRUCTION", "You are a helpful assistant.")
)
```

### YAML Configuration

```yaml
# config/production.yaml
agent:
  name: production_agent
  model: gemini-2.0-flash
  instruction: |
    You are a production assistant.
    Be concise and professional.

session:
  service: firestore
  ttl_hours: 24

logging:
  level: INFO
  format: json
```

```python
import yaml

with open("config/production.yaml") as f:
    config = yaml.safe_load(f)

agent = Agent(**config["agent"])
```

## Monitoring and Observability

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

# Wrap agent calls
def run_with_tracing(runner, user_id, session_id, message):
    with tracer.start_as_current_span("agent_run") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("session_id", session_id)

        events = []
        for event in runner.run(user_id, session_id, message):
            events.append(event)
            if hasattr(event, "tool_call"):
                with tracer.start_span("tool_call") as tool_span:
                    tool_span.set_attribute("tool_name", event.tool_call.name)

        return events
```

### Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module
        }
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("adk")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

agent_requests = Counter("agent_requests_total", "Total agent requests")
agent_latency = Histogram("agent_latency_seconds", "Agent response latency")
tool_calls = Counter("tool_calls_total", "Tool calls", ["tool_name"])

@agent_latency.time()
def handle_request(runner, user_id, session_id, message):
    agent_requests.inc()
    for event in runner.run(user_id, session_id, message):
        if hasattr(event, "tool_call"):
            tool_calls.labels(tool_name=event.tool_call.name).inc()
        yield event

# Start metrics server
start_http_server(9090)
```

## Production Checklist

### Pre-Deployment

- [ ] **Session persistence** - Use Firestore/Redis, not in-memory
- [ ] **Memory service** - Configure for cross-session context
- [ ] **API keys** - Stored in Secret Manager, not env vars
- [ ] **Rate limiting** - Protect against abuse
- [ ] **Input validation** - Sanitize user inputs
- [ ] **Error handling** - Graceful degradation

### Security

- [ ] **Authentication** - Verify user identity
- [ ] **Authorization** - Check permissions per action
- [ ] **Audit logging** - Log all agent actions
- [ ] **PII handling** - Redact sensitive data in logs
- [ ] **Network security** - VPC, firewall rules

### Reliability

- [ ] **Health checks** - Liveness and readiness probes
- [ ] **Autoscaling** - Based on CPU/memory/latency
- [ ] **Timeouts** - Set appropriate limits
- [ ] **Circuit breakers** - Handle downstream failures
- [ ] **Retries** - Exponential backoff for transient errors

### Monitoring

- [ ] **Distributed tracing** - Track request flow
- [ ] **Metrics** - Latency, error rate, throughput
- [ ] **Alerting** - On error spikes, latency degradation
- [ ] **Dashboards** - Real-time visibility
- [ ] **Log aggregation** - Centralized logging
