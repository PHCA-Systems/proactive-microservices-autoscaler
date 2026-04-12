# Citation Update Summary

## ✅ All Citations Successfully Updated!

### Changes Made to Paper/IMSA-v1.tex

#### 1. Removed Citations (No Replacement Needed)
- ❌ `\cite{microservices}` - Removed from Introduction (common knowledge)
- ❌ `\cite{keda}` - Removed from Background section (reworded to "Event-driven autoscaling systems")
- ❌ `\cite{robustperception}` - Removed from Introduction (justified scrape interval ourselves)

#### 2. Replaced with Academic Papers

**k8s-hpa → hasan2020horizontal**
- Abstract: No change needed (not cited there)
- Introduction: `\cite{k8s-hpa}` → `\cite{hasan2020horizontal}`
- System Architecture: `\cite{k8s-hpa}` → `\cite{hasan2020horizontal}`

**kep853 + netflix-titus → lorido2014autoscaling + autopilot**
- Abstract: `\cite{kep853,netflix-titus}` → `\cite{lorido2014autoscaling}`
- Introduction: `\cite{kep853}` and `\cite{netflix-titus}` → `\cite{lorido2014autoscaling}` and `\cite{autopilot}`
- Background: `\cite{kep853,netflix-titus}` → `\cite{lorido2014autoscaling,autopilot}`
- Discussion: `\cite{kep853,netflix-titus}` → `\cite{lorido2014autoscaling,autopilot}`
- Consensus Service: Added `\cite{hasan2020horizontal}` for HPA stabilization window
- Conclusion: `\cite{kep853,netflix-titus}` → `\cite{lorido2014autoscaling,hasan2020horizontal}`

**kafka → garg2023kafka**
- Introduction: `\cite{kafka}` → `\cite{garg2023kafka}` (2 instances)
- System Architecture: `\cite{kafka}` → `\cite{garg2023kafka}`
- Conclusion: `\cite{kafka}` → `\cite{garg2023kafka}`

**sockshop → villamizar2017sockshop**
- Abstract: `\cite{sockshop}` → `\cite{villamizar2017sockshop}`
- Introduction: `\cite{sockshop}` → `\cite{villamizar2017sockshop}`
- Limitations: `\cite{sockshop}` → `\cite{villamizar2017sockshop}`

#### 3. Kept as Software Tools (Reformatted)
- ✅ `\cite{prometheus}` - Kept (CNCF graduated project)
- ✅ `\cite{locust}` - Kept (open-source load testing tool)

---

## Updated References.bib File

### New Academic References (5)
1. **hasan2020horizontal** - Kubernetes HPA journal article (Symmetry, 2020)
2. **garg2023kafka** - Apache Kafka survey (IEEE Access, 2023)
3. **lorido2014autoscaling** - Autoscaling review (Journal of Grid Computing, 2014)
4. **ramsay2018response** - Response time research (Int. J. HCI, 2018)
5. **villamizar2017sockshop** - Sock Shop benchmark paper (Springer, 2017)

### Existing Academic References (10)
- pbscaler, firm, autopilot (already had)
- svm, randomforest, smote, sklearn (already had)
- ensemble, gnn (already had)

### Software Tools (2)
- prometheus (reformatted as CNCF project)
- locust (reformatted as open-source tool)

---

## Final Statistics

**Before:**
- Total references: 22
- Website/blog references: 12 (55%)
- Academic papers: 10 (45%)

**After:**
- Total references: 17
- Software tool references: 2 (12%)
- Academic papers: 15 (88%)

**Improvement:** Reduced website references from 55% to 12%!

---

## References Removed from Bibliography

These are no longer in References.bib:
1. microservices (Martin Fowler article)
2. k8s-hpa (Kubernetes docs)
3. keda (KEDA website)
4. kep853 (GitHub KEP)
5. netflix-titus (Netflix blog)
6. kafka (Apache docs - old version)
7. sockshop (GitHub repo - old version)
8. k8s-metrics (Kubernetes docs)
9. robustperception (blog post)
10. sla-web (Nielsen Norman Group)

---

## Next Steps

1. ✅ References.bib updated with academic papers
2. ✅ All citations in IMSA-v1.tex updated
3. ✅ Verified no old citation keys remain

**To compile your paper:**
```bash
pdflatex IMSA-v1.tex
bibtex IMSA-v1
pdflatex IMSA-v1.tex
pdflatex IMSA-v1.tex
```

Your supervisor should be much happier with this academically rigorous reference list!
