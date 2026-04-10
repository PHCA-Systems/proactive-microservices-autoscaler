# Tasks: GKE Data Collection Pipeline

## Task List

- [x] 1. Create GKE cluster
  - [x] 1.1 Run cluster create command
  - [x] 1.2 Fetch credentials and verify nodes

- [x] 2. Deploy Sock Shop
  - [x] 2.1 Create namespace and apply manifest (HPA disabled)
  - [x] 2.2 Wait for all pods to be Running
  - [x] 2.3 Expose front-end as LoadBalancer and capture external IP

- [x] 3. Deploy Prometheus
  - [x] 3.1 Install Helm (if not already installed)
  - [x] 3.2 Add Prometheus Helm repo and update
  - [x] 3.3 Install Prometheus with 5s scrape interval
  - [x] 3.4 Verify Prometheus via port-forward

- [x] 4. Create and configure Locust VM
  - [x] 4.1 Create the GCE VM
  - [x] 4.2 Install Python and Locust on the VM
  - [x] 4.3 Copy load testing scripts to the VM

- [x] 5. Set up local Python virtual environment for metrics aggregator
  - [x] 5.1 Create venv inside the metrics-aggregator service folder
  - [x] 5.2 Install dependencies into the venv

- [-] 6. Run data collection experiments
  - [x] 6.1 Start port-forward to Prometheus
  - [ ] 6.2 Run Constant load experiment
  - [ ] 6.3 Run Ramp load experiment
  - [ ] 6.4 Run Spike load experiment
  - [ ] 6.5 Run Step load experiment
  - [ ] 6.6 Copy collected CSV to output directory

- [ ] 7. Teardown / pause cluster between sessions

---

## Task Details

### 1. Create GKE cluster — ALREADY COMPLETE

Cluster `sock-shop-cluster` is provisioned and 3 nodes are `Ready`. Credentials are already configured locally.

Verify with:
```bash
kubectl get nodes
```

---

### 2. Deploy Sock Shop

#### 2.1 Create namespace and apply manifest (HPA disabled)

The upstream Sock Shop manifest includes HorizontalPodAutoscaler resources. Since you do not want any autoscaling during experiments, strip them out before applying.

Download the manifest, remove all HPA objects, then apply:

```bash
# Download manifest
curl -o /tmp/complete-demo.yaml \
  https://raw.githubusercontent.com/microservices-demo/microservices-demo/master/deploy/kubernetes/complete-demo.yaml

# Remove all HorizontalPodAutoscaler sections
grep -v "kind: HorizontalPodAutoscaler" /tmp/complete-demo.yaml | \
  awk '/^---/{buf=""; next} {buf=buf"\n"$0} /kind: HorizontalPodAutoscaler/{buf=""; skip=1} skip && /^$/{skip=0; next} !skip{print}' \
  > /tmp/complete-demo-no-hpa.yaml
```

A cleaner approach — use `kubectl` to apply and then immediately delete any HPAs that sneak through:

```bash
kubectl create namespace sock-shop

kubectl apply -n sock-shop -f \
  https://raw.githubusercontent.com/microservices-demo/microservices-demo/master/deploy/kubernetes/complete-demo.yaml

# Delete any HPAs that were created
kubectl delete hpa --all -n sock-shop
```

Verify no HPAs remain:
```bash
kubectl get hpa -n sock-shop
```

Expected: `No resources found in sock-shop namespace.`

#### 2.2 Wait for all pods to be Running

```bash
kubectl get pods -n sock-shop -w
```

Wait until all pods show `Running` and `1/1` ready (typically ~5 minutes). The Java services (`carts`, `orders`) take longest due to JVM startup. Press Ctrl+C when stable.

Quick non-watch check:
```bash
kubectl get pods -n sock-shop
```

#### 2.3 Expose front-end as LoadBalancer and capture external IP

```bash
kubectl patch svc front-end -n sock-shop \
  -p '{"spec": {"type": "LoadBalancer"}}'
```

Watch for the external IP (~2 minutes):
```bash
kubectl get svc front-end -n sock-shop -w
```

Once `EXTERNAL-IP` is no longer `<pending>`, capture it:
```bash
export SOCK_SHOP_IP=$(kubectl get svc front-end -n sock-shop \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Sock Shop external IP: $SOCK_SHOP_IP"
```

Verify it's reachable:
```bash
curl -s -o /dev/null -w "%{http_code}" http://$SOCK_SHOP_IP
```

Expected: `200`.

---

### 3. Deploy Prometheus

#### 3.1 Install Helm (if not already installed)

```bash
helm version
```

If not installed:
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### 3.2 Add Prometheus Helm repo and update

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

#### 3.3 Install Prometheus with 10s scrape interval

```bash
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --create-namespace \
  --set server.global.scrape_interval=5s \
  --set server.global.evaluation_interval=5s \
  --set alertmanager.enabled=false \
  --set pushgateway.enabled=false
```

Wait for the server pod to be ready:
```bash
kubectl get pods -n monitoring -w
```

Press Ctrl+C when `prometheus-server-*` shows `Running 1/1`.

#### 3.4 Verify Prometheus via port-forward

```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:80 &
```

Open http://localhost:9090 and run:
```
request_duration_seconds_count
```

You should see results for Sock Shop services (`carts`, `catalogue`, `front-end`, etc.). If you see no results yet, wait 1–2 minutes for Prometheus to scrape the first cycle.

---

### 4. Create and configure Locust VM

#### 4.1 Create the GCE VM

```bash
gcloud compute instances create locust-runner \
  --machine-type=e2-small \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=locust-vm
```

#### 4.2 Install Python and Locust on the VM

```bash
gcloud compute ssh locust-runner --zone=us-central1-a
```

On the VM:
```bash
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv
python3 -m venv ~/locust-venv
source ~/locust-venv/bin/activate
pip install locust
locust --version
exit
```

#### 4.3 Copy load testing scripts to the VM

From your local machine (run from the repo root `d:\Projects\Grad\PHCA`):
```bash
gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/locustfile.py \
  locust-runner:~/locustfile.py

gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/load_shapes.py \
  locust-runner:~/load_shapes.py

gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/locustfile_constant.py \
  locust-runner:~/locustfile_constant.py

gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/locustfile_ramp.py \
  locust-runner:~/locustfile_ramp.py

gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/locustfile_spike.py \
  locust-runner:~/locustfile_spike.py

gcloud compute scp --zone=us-central1-a \
  kafka-structured/load-testing/src/locustfile_step.py \
  locust-runner:~/locustfile_step.py
```

Verify:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a --command="ls ~/*.py"
```

---

### 5. Set up local Python virtual environment for metrics aggregator

The metrics aggregator runs locally (not in Docker) for data collection. It needs its own venv since this is a separate folder from the main branch.

#### 5.1 Create venv inside the metrics-aggregator service folder

```bash
cd kafka-structured/services/metrics-aggregator
python -m venv venv
```

#### 5.2 Install dependencies into the venv

On Windows (bash):
```bash
source venv/Scripts/activate
pip install -r requirements.txt
```

Verify:
```bash
python -c "import requests, pandas; print('OK')"
```

Note: `kafka-python` is in requirements.txt but is not used in development mode — it will still install fine, just won't be called.

Keep this venv activated whenever running the metrics aggregator in tasks 6.x.

---

### 6. Run data collection experiments

Each experiment: port-forward must be running (6.1), start aggregator in Terminal 1, run Locust on VM in Terminal 2, stop aggregator when Locust finishes.

The CSV appends across runs — all four experiments write to the same file, giving you a mixed-pattern dataset equivalent to your existing `mixed_4hour_metrics.csv`.

#### 6.1 Start port-forward to Prometheus

Run in a dedicated terminal and keep it open for all experiments:
```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
```

If one is already running from task 3.4:
```bash
pkill -f "kubectl port-forward"
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
```

#### 6.2 Run Constant load experiment

**Terminal 1 — metrics aggregator** (activate venv first):
```bash
cd kafka-structured/services/metrics-aggregator
source venv/Scripts/activate
mkdir -p output
MODE=development \
  PROMETHEUS_URL=http://localhost:9090 \
  POLL_INTERVAL_SEC=30 \
  OUTPUT_DIR=./output \
  python app.py
```

**Terminal 2 — Locust on VM** (replace `EXTERNAL_IP`):
```bash
gcloud compute ssh locust-runner --zone=us-central1-a
source ~/locust-venv/bin/activate
locust -f locustfile_constant.py --headless --users 50 --spawn-rate 5 --run-time 20m --host http://EXTERNAL_IP
```

When Locust finishes, Ctrl+C the aggregator in Terminal 1.

#### 6.3 Run Ramp load experiment

**Terminal 1 — metrics aggregator**:
```bash
cd kafka-structured/services/metrics-aggregator
source venv/Scripts/activate
MODE=development \
  PROMETHEUS_URL=http://localhost:9090 \
  POLL_INTERVAL_SEC=30 \
  OUTPUT_DIR=./output \
  python app.py
```

**Terminal 2 — Locust on VM**:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a
source ~/locust-venv/bin/activate
locust -f locustfile_ramp.py --headless --host http://EXTERNAL_IP
```

#### 6.4 Run Spike load experiment

**Terminal 1 — metrics aggregator**:
```bash
cd kafka-structured/services/metrics-aggregator
source venv/Scripts/activate
MODE=development \
  PROMETHEUS_URL=http://localhost:9090 \
  POLL_INTERVAL_SEC=30 \
  OUTPUT_DIR=./output \
  python app.py
```

**Terminal 2 — Locust on VM**:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a
source ~/locust-venv/bin/activate
locust -f locustfile_spike.py --headless --host http://EXTERNAL_IP
```

#### 6.5 Run Step load experiment

**Terminal 1 — metrics aggregator**:
```bash
cd kafka-structured/services/metrics-aggregator
source venv/Scripts/activate
MODE=development \
  PROMETHEUS_URL=http://localhost:9090 \
  POLL_INTERVAL_SEC=30 \
  OUTPUT_DIR=./output \
  python app.py
```

**Terminal 2 — Locust on VM**:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a
source ~/locust-venv/bin/activate
locust -f locustfile_step.py --headless --host http://EXTERNAL_IP
```

#### 6.6 Copy collected CSV to output directory

```bash
cp kafka-structured/services/metrics-aggregator/output/sockshop_metrics.csv \
   kafka-structured/output/csv/gke_sockshop_metrics.csv
```

Check row count:
```bash
wc -l kafka-structured/output/csv/gke_sockshop_metrics.csv
```

Preview:
```bash
head -5 kafka-structured/output/csv/gke_sockshop_metrics.csv
```

---

### 7. Teardown / pause cluster between sessions

#### Pause (between sessions — preserves deployments, stops billing)

```bash
gcloud container clusters resize sock-shop-cluster \
  --num-nodes=0 \
  --region=us-central1

gcloud compute instances stop locust-runner --zone=us-central1-a
```

#### Resume

```bash
gcloud container clusters resize sock-shop-cluster \
  --num-nodes=3 \
  --region=us-central1

gcloud compute instances start locust-runner --zone=us-central1-a

gcloud container clusters get-credentials sock-shop-cluster --region=us-central1

kubectl get pods -n sock-shop
kubectl get pods -n monitoring
```

After resize, verify no HPAs crept back in:
```bash
kubectl get hpa -n sock-shop
```

#### Full teardown (when data collection is complete)

```bash
gcloud container clusters delete sock-shop-cluster --region=us-central1
gcloud compute instances delete locust-runner --zone=us-central1-a
```
