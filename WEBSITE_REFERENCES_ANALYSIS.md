# Website References Analysis

## Summary
Your supervisor is correct - you have **11 website/documentation references** out of 22 total references (50%). Academic papers typically expect peer-reviewed sources (journal articles, conference proceedings).

---

## Website References (Need Replacement)

### 1. **k8s-hpa** - Kubernetes Documentation
- **Type**: Official documentation website
- **URL**: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- **Cited in paper at**:
  - Abstract (line 41): "industry practice~\cite{kep853,netflix-titus}"
  - Introduction (line 50): "remains structurally reactive~\cite{k8s-hpa}"
  - System Architecture section (line ~137): "by invoking the Kubernetes API~\cite{k8s-hpa}"

### 2. **keda** - KEDA Website
- **Type**: Project website
- **URL**: https://keda.sh/
- **Cited in paper at**:
  - Background section (line 70): "KEDA (Kubernetes Event-Driven Autoscaling)~\cite{keda}"

### 3. **kafka** - Apache Kafka Documentation
- **Type**: Official documentation website
- **URL**: https://kafka.apache.org/documentation/
- **Cited in paper at**:
  - Introduction (line 54): "through Apache Kafka topics~\cite{kafka}"
  - Background section: "Apache Kafka has emerged..."
  - System Architecture section (line ~137): "two Kafka topics~\cite{kafka}"
  - Conclusion: "through Kafka topics~\cite{kafka}"

### 4. **sockshop** - GitHub Repository
- **Type**: GitHub repository
- **URL**: https://github.com/microservices-demo/microservices-demo
- **Cited in paper at**:
  - Abstract (line 41): "Sock Shop benchmark~\cite{sockshop}"
  - Introduction (line 56): "Sock Shop microservices benchmark~\cite{sockshop}"

### 5. **locust** - Locust Website
- **Type**: Project website
- **URL**: https://locust.io/
- **Cited in paper at**:
  - Abstract (line 41): "Locust-generated ramp load profiles~\cite{locust}"
  - Introduction (line 56): "using Locust~\cite{locust}"

### 6. **prometheus** - Prometheus Documentation
- **Type**: Official documentation website
- **URL**: https://prometheus.io/docs/
- **Cited in paper at**:
  - Introduction (line 56): "scraped from Prometheus~\cite{prometheus}"
  - System Architecture section: "polls Prometheus~\cite{prometheus}"

### 7. **robustperception** - Blog Post
- **Type**: Technical blog
- **URL**: https://www.robustperception.io/how-long-should-prometheus-scrape-intervals-be
- **Cited in paper at**:
  - Introduction (line 56): "Prometheus scrape interval range~\cite{robustperception}"

### 8. **kep853** - Kubernetes Enhancement Proposal (GitHub)
- **Type**: GitHub documentation
- **URL**: https://github.com/kubernetes/enhancements/tree/master/keps/sig-autoscaling/853-configurable-hpa-scale-down-stabilization-window
- **Cited in paper at**:
  - Abstract (line 41): "industry practice~\cite{kep853,netflix-titus}"
  - Introduction (line 54): "Kubernetes Enhancement Proposal 853~\cite{kep853}"
  - Background section: "validated against Kubernetes KEP-853~\cite{kep853}"
  - Conclusion: "validated against Kubernetes KEP-853~\cite{kep853}"

### 9. **netflix-titus** - Netflix Tech Blog
- **Type**: Company blog post
- **URL**: https://netflixtechblog.com/auto-scaling-production-services-on-titus-1f3cd49f5cd7
- **Cited in paper at**:
  - Abstract (line 41): "industry practice~\cite{kep853,netflix-titus}"
  - Introduction (line 54): "Netflix's Titus autoscaling system~\cite{netflix-titus}"
  - Background section: "Netflix Titus documentation~\cite{netflix-titus}"
  - Conclusion: "Netflix Titus documentation~\cite{netflix-titus}"

### 10. **k8s-metrics** - Kubernetes Documentation
- **Type**: Official documentation website
- **URL**: https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/
- **Cited in paper at**:
  - Background section: References to Metrics Server

### 11. **sla-web** - Nielsen Norman Group Article
- **Type**: Web article
- **URL**: https://www.nngroup.com/articles/response-times-3-important-limits/
- **Cited in paper at**:
  - (Need to search for exact location - likely in SLA discussion)

### 12. **microservices** - Martin Fowler Article
- **Type**: Web article
- **URL**: https://martinfowler.com/articles/microservices.html
- **Cited in paper at**:
  - Introduction (line 50): "elastic resource allocation as a first-class property~\cite{microservices}"

---

## Peer-Reviewed References (Good - Keep These)

### Journal Articles (5)
1. **pbscaler** - IEEE Transactions on Services Computing (2017)
2. **svm** - Machine Learning journal (1995)
3. **randomforest** - Machine Learning journal (2001)
4. **smote** - Journal of Artificial Intelligence Research (2002)
5. **sklearn** - Journal of Machine Learning Research (2011)

### Conference Proceedings (3)
1. **firm** - USENIX OSDI (2020)
2. **autopilot** - EuroSys (2020)
3. **ensemble** - Multiple Classifier Systems Workshop (2000)
4. **gnn** - ICLR (2017)

---

## Recommendations

### High Priority - Find Academic Alternatives:
1. **Kubernetes HPA** - Look for academic papers evaluating Kubernetes autoscaling
2. **Apache Kafka** - Find the original Kafka paper or academic evaluations
3. **KEP-853 & Netflix Titus** - Search for academic papers on autoscaling policies
4. **Microservices** - Find academic survey papers on microservice architectures

### Medium Priority - May Need to Keep:
1. **Sock Shop** - Benchmark tool, may be acceptable as "software" reference
2. **Locust** - Load testing tool, may be acceptable as "software" reference
3. **Prometheus** - Monitoring tool, may be acceptable as "software" reference

### Low Priority - Consider Removing:
1. **KEDA** - Can you remove this citation entirely?
2. **Robust Perception blog** - Find academic source for scrape interval justification
3. **Nielsen Norman Group** - Find academic HCI paper on response times
4. **Martin Fowler article** - Find academic microservices survey paper

---

## Action Items

1. Search Google Scholar for:
   - "Kubernetes autoscaling" + "conference" or "journal"
   - "Apache Kafka" + "original paper"
   - "microservices architecture" + "survey"
   - "container orchestration" + "autoscaling"

2. Check if these tools have associated academic papers:
   - Sock Shop may have a demo paper
   - Prometheus may have a systems paper
   - Locust may have a tool paper

3. For industry practices (KEP-853, Netflix):
   - Look for academic papers that cite these practices
   - Search for autoscaling policy papers that reference them

4. Consider adding more recent academic work on:
   - ML-based autoscaling (2020-2024)
   - Kubernetes performance evaluation
   - Microservices resource management
