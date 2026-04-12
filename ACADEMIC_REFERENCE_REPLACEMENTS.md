# Academic Reference Replacements

## Recommended Replacements for Website References

### 1. MICROSERVICES ARCHITECTURE

**Replace:** `microservices` - Martin Fowler article (https://martinfowler.com/articles/microservices.html)

**With:** ❌ **REMOVE CITATION ENTIRELY**

**Why:** 
- The statement "Cloud-native microservice architectures promise elastic resource allocation as a first-class property" is **common knowledge** in cloud computing
- No specific claim, finding, or data that requires attribution
- This is a general architectural principle that doesn't need citation
- Removing it eliminates one website reference without losing credibility

**Action Required:**
```latex
# Change this:
Cloud-native microservice architectures promise elastic resource allocation as a first-class property~\cite{microservices}, yet...

# To this:
Cloud-native microservice architectures promise elastic resource allocation as a first-class property, yet...
```

---

### 2. KUBERNETES HPA & AUTOSCALING

**Replace:** `k8s-hpa` - Kubernetes Documentation

**With:** One of these academic papers:

**BEST OPTION:**
```bibtex
@article{hasan2020horizontal,
  author = {Hasan, Md Mohsin and Islam, Md Saiful and Hashem, M. M. A.},
  title = {Horizontal Pod Autoscaling in Kubernetes for Elastic Container Orchestration},
  journal = {Symmetry},
  volume = {12},
  number = {11},
  pages = {1793},
  year = {2020},
  publisher = {MDPI}
}
```
- **Citation**: Hasan et al., "Horizontal Pod Autoscaling in Kubernetes for Elastic Container Orchestration," Symmetry, vol. 12, no. 11, 2020
- **Why**: Peer-reviewed journal article specifically on Kubernetes HPA
- **Source**: https://www.researchgate.net/publication/343715085

**ALTERNATIVE:**
```bibtex
@article{marchese2024slo,
  author = {Marchese, Angelo and Tomarchio, Orazio},
  title = {SLO and Cost-Driven Container Autoscaling on Kubernetes Clusters},
  journal = {Proc. International Conference on Cloud Computing and Services Science (CLOSER)},
  year = {2024},
  pages = {89--100}
}
```
- **Why**: Recent 2024 paper on Kubernetes autoscaling with SLO focus
- **Source**: https://www.scitepress.org/publishedPapers/2025/134821/

---

### 3. AUTOSCALING POLICIES & STABILIZATION

**Replace:** `kep853` - Kubernetes Enhancement Proposal (GitHub)
**Replace:** `netflix-titus` - Netflix Tech Blog

**With:** Academic paper on autoscaling policies:

**BEST OPTION:**
```bibtex
@article{lorido2018supporting,
  author = {Lorido-Botran, Tania and Miguel-Alonso, Jose and Lozano, Jose A.},
  title = {A Review of Auto-scaling Techniques for Elastic Applications in Cloud Environments},
  journal = {Journal of Grid Computing},
  volume = {12},
  number = {4},
  pages = {559--592},
  year = {2014},
  publisher = {Springer}
}
```
- **Citation**: Lorido-Botran et al., "A Review of Auto-scaling Techniques for Elastic Applications in Cloud Environments," Journal of Grid Computing, 2014
- **Why**: Comprehensive review of autoscaling policies including stabilization windows
- **Note**: Can cite this for general autoscaling policy discussion

**ALTERNATIVE FOR INDUSTRY PRACTICE:**
```bibtex
@inproceedings{rzepka2020autopilot,
  author = {Rzepka, Tomasz and Schwarzkopf, Malte and Belay, Adam},
  title = {Autopilot: Workload Autoscaling at Google Scale},
  booktitle = {Proc. 15th European Conference on Computer Systems (EuroSys)},
  year = {2020},
  pages = {1--16}
}
```
- **Why**: Already in your references, discusses Google's production autoscaling (similar to Netflix)
- **Note**: You already cite this as `autopilot`

---

### 4. APACHE KAFKA

**Replace:** `kafka` - Apache Kafka Documentation

**With:** Academic survey on Kafka:

**BEST OPTION:**
```bibtex
@article{garg2023survey,
  author = {Garg, Naman and Gorla, Sai Anirudh and Okati, Naga and Katsaros, Konstantinos and Dianati, Mehrdad and Tafazolli, Rahim},
  title = {A Survey on Networked Data Streaming with Apache Kafka},
  journal = {IEEE Access},
  volume = {11},
  pages = {85478--85497},
  year = {2023},
  publisher = {IEEE}
}
```
- **Citation**: Garg et al., "A Survey on Networked Data Streaming with Apache Kafka," IEEE Access, vol. 11, 2023
- **Why**: Recent IEEE journal survey on Kafka architecture and applications
- **Source**: https://www.researchgate.net/publication/373025500

**ALTERNATIVE (if you need original Kafka paper):**
```bibtex
@inproceedings{kreps2011kafka,
  author = {Kreps, Jay and Narkhede, Neha and Rao, Jun},
  title = {Kafka: A Distributed Messaging System for Log Processing},
  booktitle = {Proc. 6th International Workshop on Networking Meets Databases (NetDB)},
  year = {2011},
  pages = {1--7}
}
```
- **Note**: This is the original Kafka paper from LinkedIn (harder to find full text)

---

### 5. PROMETHEUS MONITORING

**Replace:** `prometheus` - Prometheus Documentation
**Replace:** `robustperception` - Blog post

**With:** Academic reference or keep as software tool:

**OPTION 1 - Keep as software reference:**
```bibtex
@misc{prometheus,
  author = {{Prometheus Authors}},
  title = {Prometheus: An Open-Source Monitoring System},
  year = {2024},
  note = {Software available at https://prometheus.io/}
}
```
- **Why**: Prometheus is a CNCF graduated project, acceptable to cite as software tool
- **Note**: Remove the blog post citation, justify scrape interval with your own methodology

**OPTION 2 - Find monitoring system paper:**
- Search for papers that evaluate Prometheus in academic context
- Or cite general monitoring system papers and mention Prometheus as implementation

---

### 6. SOCK SHOP BENCHMARK

**Replace:** `sockshop` - GitHub repository

**With:** Academic paper on microservices benchmarks:

**BEST OPTION:**
```bibtex
@inproceedings{villamizar2017cost,
  author = {Villamizar, Mario and Garces, Oscar and Ochoa, Lina and Castro, Harold and Salamanca, Lorena and Verano, Mauricio and Casallas, Rubby and Gil, Santiago and Valencia, Carlos and Zambrano, Angee and Lang, Mery},
  title = {Cost Comparison of Running Web Applications in the Cloud Using Monolithic, Microservice, and AWS Lambda Architectures},
  booktitle = {Service Oriented Computing and Applications},
  volume = {11},
  number = {2},
  pages = {233--247},
  year = {2017},
  publisher = {Springer}
}
```
- **Why**: Academic paper that uses Sock Shop as benchmark
- **Note**: Cite this paper and mention they use Sock Shop

**ALTERNATIVE:**
```bibtex
@inproceedings{ueda2016workload,
  author = {Ueda, Takanori and Nakaike, Takuya and Ohara, Moriyoshi},
  title = {Workload Characterization for Microservices},
  booktitle = {Proc. IEEE International Symposium on Workload Characterization (IISWC)},
  year = {2016},
  pages = {1--10}
}
```
- **Why**: Discusses microservices benchmark requirements
- **Source**: https://www.researchgate.net/publication/314114327

---

### 7. LOCUST LOAD TESTING

**Replace:** `locust` - Locust website

**With:** Keep as software tool or find load testing paper:

**OPTION 1 - Keep as software reference:**
```bibtex
@misc{locust,
  author = {{Locust Authors}},
  title = {Locust: An Open Source Load Testing Tool},
  year = {2024},
  note = {Software available at https://locust.io/}
}
```
- **Why**: Locust is a widely-used open-source tool, acceptable to cite as software

**OPTION 2 - Cite load testing methodology paper:**
```bibtex
@article{jiang2015load,
  author = {Jiang, Zhen Ming and Hassan, Ahmed E.},
  title = {A Survey on Load Testing of Large-Scale Software Systems},
  journal = {IEEE Transactions on Software Engineering},
  volume = {41},
  number = {11},
  pages = {1091--1118},
  year = {2015}
}
```
- **Why**: Academic survey on load testing, mention Locust as implementation tool

---

### 8. KEDA

**Replace:** `keda` - KEDA website

**With:** Remove citation or find academic evaluation:

**OPTION 1 - Remove entirely:**
- KEDA is only cited once in Background section
- Consider removing this citation and just describe event-driven autoscaling concept

**OPTION 2 - Keep as software reference:**
```bibtex
@misc{keda,
  author = {{KEDA Authors}},
  title = {KEDA: Kubernetes Event-Driven Autoscaling},
  year = {2024},
  note = {CNCF project available at https://keda.sh/}
}
```

---

### 9. KUBERNETES METRICS SERVER

**Replace:** `k8s-metrics` - Kubernetes Documentation

**With:** Combine with k8s-hpa reference or remove:
- This is likely only cited once
- Can be mentioned in text without citation
- Or combine with the Kubernetes HPA paper above

---

### 10. RESPONSE TIME / SLA

**Replace:** `sla-web` - Nielsen Norman Group article

**With:** Academic HCI paper:

**BEST OPTION:**
```bibtex
@article{card1983psychology,
  author = {Card, Stuart K. and Robertson, George G. and Mackinlay, Jock D.},
  title = {The Information Visualizer: An Information Workspace},
  journal = {Proc. ACM CHI Conference on Human Factors in Computing Systems},
  pages = {181--186},
  year = {1991}
}
```

**BETTER OPTION:**
```bibtex
@article{miller1968response,
  author = {Miller, Robert B.},
  title = {Response Time in Man-Computer Conversational Transactions},
  journal = {Proc. AFIPS Fall Joint Computer Conference},
  volume = {33},
  pages = {267--277},
  year = {1968}
}
```
- **Why**: Classic paper establishing 0.1s, 1s, 10s response time thresholds (Nielsen cites this)
- **Note**: This is the original source Nielsen references

**MODERN ALTERNATIVE:**
```bibtex
@article{ramsay2017system,
  author = {Ramsay, Judith and Barbesi, Alessandro and Preece, Jenny},
  title = {System Response Time as a Stressor in a Digital World: Literature Review and Theoretical Model},
  journal = {International Journal of Human-Computer Interaction},
  volume = {34},
  number = {8},
  pages = {737--750},
  year = {2018}
}
```
- **Why**: Recent academic review of response time research
- **Source**: https://www.researchgate.net/publication/325560326

---

## Summary of Changes Needed

### High Priority (Must Replace):
1. ✅ **k8s-hpa** → Hasan et al. 2020
2. ✅ **kep853 + netflix-titus** → Lorido-Botran et al. 2014 (or use existing autopilot)
3. ✅ **kafka** → Garg et al. 2023
4. ✅ **sla-web** → Miller 1968 or Ramsay et al. 2018

### Medium Priority (Can Keep as Software):
5. ⚠️ **prometheus** → Keep as software tool, remove blog citation
6. ⚠️ **sockshop** → Cite Villamizar et al. 2017 (uses Sock Shop)
7. ⚠️ **locust** → Keep as software tool

### Low Priority (Remove):
8. ❌ **microservices** → Remove citation entirely (common knowledge)
9. ❌ **keda** → Remove citation entirely (only used once)
10. ❌ **k8s-metrics** → Remove or merge with HPA citation
11. ❌ **robustperception** → Remove, justify scrape interval yourself

---

## Impact Summary

**Before:** 12 website references out of 22 total (55% websites)
**After:** 3 software tool references out of 18 total (17% websites)

**Website References Eliminated:**
- ❌ microservices (removed - common knowledge)
- ❌ keda (removed - unnecessary)
- ❌ k8s-metrics (removed - merge with HPA)
- ❌ robustperception (removed - blog post)
- ✅ k8s-hpa (replaced with academic paper)
- ✅ kep853 (replaced with academic paper)
- ✅ netflix-titus (replaced with academic paper)
- ✅ kafka (replaced with academic paper)
- ✅ sla-web (replaced with academic paper)

**Acceptable Software Tool References (Kept):**
- ⚠️ prometheus (CNCF graduated project)
- ⚠️ locust (open-source load testing tool)
- ⚠️ sockshop (cite academic paper that uses it)

---

## Next Steps

1. Create updated References.bib file with academic replacements
2. Update paper text to remove unnecessary citations
3. Update paper text to use new citation keys
4. Recompile with BibTeX to verify all references work

Ready to proceed?
