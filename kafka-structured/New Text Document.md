Phase 0 — Local prerequisites (do this today, \~30 min)

1\. Install gcloud CLI

bash# macOS

brew install --cask google-cloud-sdk



\# Or direct installer

curl https://sdk.cloud.google.com | bash

exec -l $SHELL

2\. Install kubectl (you likely have this from minikube, verify)

bashkubectl version --client

3\. Install the GKE auth plugin (required for GKE clusters)

bashgcloud components install gke-gcloud-auth-plugin



Phase 1 — GCP account and project setup (\~20 min)

1\. Create a GCP account

Go to console.cloud.google.com. Use a Google account. You get $300 credit, valid 90 days. You must enter a credit card but you will not be charged unless you manually upgrade after credits are exhausted.

2\. Create a project

bashgcloud auth login

gcloud projects create sock-shop-research --name="Sock Shop Research"

gcloud config set project sock-shop-research

3\. Enable required APIs

bashgcloud services enable container.googleapis.com

gcloud services enable compute.googleapis.com

4\. Set your region

Choose us-central1 — it's the cheapest and has the best availability for e2 instances.

bashgcloud config set compute/region us-central1

gcloud config set compute/zone us-central1-a



Phase 2 — Create the GKE cluster (\~15 min setup, \~10 min to provision)

1\. Create the cluster

bashgcloud container clusters create sock-shop-cluster \\

&#x20; --num-nodes=3 \\

&#x20; --machine-type=e2-standard-4 \\

&#x20; --region=us-central1 \\

&#x20; --release-channel=regular \\

&#x20; --no-enable-autoupgrade

e2-standard-4 = 4 vCPU, 16GB RAM per node. Three of these gives you 12 vCPU and 48GB total — enough headroom for Sock Shop's 11 services plus Prometheus plus room for HPA to actually scale pods into.

\--no-enable-autoupgrade prevents GKE from restarting nodes mid-experiment.

This takes about 5–10 minutes. While it provisions:

2\. Get credentials once it's ready

bashgcloud container clusters get-credentials sock-shop-cluster --region=us-central1

kubectl get nodes  # verify 3 nodes show Ready



Phase 3 — Deploy Sock Shop (\~10 min)

1\. Create namespace and deploy

bashkubectl create namespace sock-shop

kubectl apply -n sock-shop -f https://raw.githubusercontent.com/microservices-demo/microservices-demo/master/deploy/kubernetes/complete-demo.yaml

2\. Wait for all pods to be Running

bashkubectl get pods -n sock-shop -w

This takes 3–5 minutes. The Java services (carts, orders) take longest due to JVM startup. Don't proceed until all pods show Running and 1/1 ready.

3\. Expose the front-end externally

The default Sock Shop manifest exposes the front-end as a NodePort. You need a LoadBalancer to get a stable external IP:

bashkubectl patch svc front-end -n sock-shop \\

&#x20; -p '{"spec": {"type": "LoadBalancer"}}'

Wait for the external IP to be assigned:

bashkubectl get svc front-end -n sock-shop -w

Once EXTERNAL-IP shows an IP (not <pending>), note it — this is the IP your Locust VM will target.



Phase 4 — Deploy Prometheus (\~10 min)

You need Prometheus running in-cluster to scrape Sock Shop metrics. The simplest path is the community Helm chart.

1\. Install Helm if you don't have it

bashbrew install helm

2\. Add the Prometheus community chart

bashhelm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm repo update

3\. Install with a short scrape interval

bashhelm install prometheus prometheus-community/prometheus \\

&#x20; --namespace monitoring \\

&#x20; --create-namespace \\

&#x20; --set server.global.scrape\_interval=10s \\

&#x20; --set server.global.evaluation\_interval=10s \\

&#x20; --set alertmanager.enabled=false \\

&#x20; --set pushgateway.enabled=false

The scrape\_interval=10s is your 10-second polling interval from the previous discussion — set it here at the source.

4\. Verify Prometheus can see Sock Shop pods

bashkubectl port-forward -n monitoring svc/prometheus-server 9090:80 \&

Open http://localhost:9090 and run the query container\_cpu\_usage\_seconds\_total — you should see results for Sock Shop containers.



Phase 5 — Create the Locust VM (\~10 min)

This runs outside the cluster, in the same GCP region.

1\. Create a small VM

bashgcloud compute instances create locust-runner \\

&#x20; --machine-type=e2-small \\

&#x20; --zone=us-central1-a \\

&#x20; --image-family=ubuntu-2204-lts \\

&#x20; --image-project=ubuntu-os-cloud \\

&#x20; --tags=locust-vm

2\. SSH in

bashgcloud compute ssh locust-runner --zone=us-central1-a

3\. Install Python and Locust

bashsudo apt-get update \&\& sudo apt-get install -y python3-pip

pip3 install locust

4\. Copy your Locust scripts to the VM

From your local machine (in a new terminal):

bashgcloud compute scp --zone=us-central1-a \\

&#x20; ./locust/locustfile.py \\

&#x20; locust-runner:\~/locustfile.py



Phase 6 — Run your first data collection experiment

1\. On the Locust VM, run a pattern (replace EXTERNAL\_IP with Sock Shop's IP)

bashlocust -f locustfile.py \\

&#x20; --headless \\

&#x20; --users 50 \\

&#x20; --spawn-rate 10 \\

&#x20; --run-time 20m \\

&#x20; --host http://EXTERNAL\_IP \\

&#x20; --pattern constant \\

&#x20; --csv /tmp/locust\_constant

2\. Simultaneously, on your local machine, run your metrics export script

You'll need a script that queries Prometheus over port-forward and writes to CSV. You already have your Kafka consumer pipeline partially designed — for now, a simple Prometheus query script is fine:

bashkubectl port-forward -n monitoring svc/prometheus-server 9090:80

Then a Python script that hits http://localhost:9090/api/v1/query\_range every 10 seconds and writes rows. We can build this script together as the next step once the cluster is up.



Phase 7 — Teardown after each session

Critical: shut down the cluster when not running experiments. At \~$0.50/hr running, leaving it on overnight burns $4–6 of your $300 credit for nothing.

bash# Stop the cluster (nodes off, control plane stays, resumes in seconds)

gcloud container clusters resize sock-shop-cluster \\

&#x20; --num-nodes=0 \\

&#x20; --region=us-central1



\# Or delete entirely (faster to recreate than you think)

gcloud container clusters delete sock-shop-cluster --region=us-central1



\# Always stop the Locust VM too

gcloud compute instances stop locust-runner --zone=us-central1-a

For your usage pattern — running experiments in sessions — resize to 0 nodes between sessions rather than deleting, so you don't have to redeploy Sock Shop each time. Resizing back up:

bashgcloud container clusters resize sock-shop-cluster \\

&#x20; --num-nodes=3 \\

&#x20; --region=us-central1

