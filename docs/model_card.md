# Model card — HybridRecMCP 2.0

**Developer:** Nada Bastawi (GitHub repository commit evidence). Original documentation
credited GitHub Copilot assistance; OpenAI Codex assisted this refactor and validation.
**License:** MIT. **Status:** independent, unofficial synthetic-data proof of concept.
Not commissioned, endorsed or integrated by a real pest-control company.

## Intended use

Local staff-workflow demonstrations, technical review and portfolio discussion.
Suggest possible service conversations, never diagnose infestations, prescribe treatment,
assess validated environmental/health risk or promise a service deadline. No automated
customer outreach, booking or operational action is implemented.

## Model and data

One-hot property/region features, clipped age scaling and configured flags feed cosine
service-affinity relevance. Service centroids use highly rated training interactions.
Iterative SVD completes missing ratings from smoothed priors without labeling unobserved
entries explicit dislikes. Bounded content and rating/5 signals combine using
validation-selected weights. Cold-start ranking uses profile affinity. Eligibility
rules apply before ranking output; repeat visits remain eligible for recurring services.

Gradient boosting learns noisy hand-authored priority labels from service, property,
region, season, building age and elapsed time. Its output is a simulation estimate
bounded 1–10, separate from relevance. The rule baseline knows the simulator and may
outperform the learned estimator. No calibrated uncertainty is claimed.

The dataset contains 500 synthetic static property profiles, 3,000 completed simulated
visits and ten illustrative services. Default combined data: 375 Tucson, 125 Ohio.
Names/emails are absent. See the data card and regional assumptions for provenance.

## Evaluation

See `reports/evaluation.json` and `docs/evaluation.md` for actual verified measurements.
The old 96.2% Precision@5 and 0.867 RMSE claims are withdrawn as current-model evidence.

Twenty percent of customers are excluded from all fitting and tuning. Warm-customer
bookings are split globally by date, with complete-date boundaries, into approximately
60/20/20 training/validation/test windows. Only validation selects content weight/SVD
rank. Train+validation then fits the final evaluation model. Warm test ranking and
reserved cold-customer test-period ranking are distinct. Metrics include HitRate@5,
Precision@5, Recall@5, binary NDCG@5 and catalog coverage. Popularity and hand-authored
profile rules use the same eligibility policy. Urgency MAE/RMSE use held-out service
events and compare gradient boosting, the noise-free generator rule and training mean.

Urgency evaluation conditions on the actual event's context, including prior visit gap;
it is not a forecast made at the beginning of the ranking window. Ranking queries are
frozen at the test-window start. Relevance labels are future bookings, not expert
judgments. Future unbooked services are unobserved rather than proven irrelevant.

## Limitations

Synthetic labels and generator-correlated baselines constrain all conclusions. A tiny
catalog inflates top-five hit rates; one seed/split supplies no uncertainty intervals.
No real customer outcomes, measured lift, verified company prices or production traffic
are available. Static building age does not track aging over the observation window.
Location groupings are illustrative. Only coarse supported property categories are
accepted publicly; unseen ZIPs return a limited-location explanation.

## Operational and fairness considerations

API keys are required; Sentry is opt-in and privacy-scrubbed. Coarse prediction features
are logged without customer IDs, ZIPs, names or email, with rotation. Such logs still
need restricted access and a retention policy for any real pilot. Drift diagnostics
measure logged distribution changes, not accuracy or fairness. No sensitive-group
fairness study, rate limiting, multi-user authorization or compliance certification
has been performed. Property and location proxies require expert and governance review.

Artifacts are trusted local joblib files, fingerprinted by data/config/code and relevant
package/Python versions. No current model size, latency SLA or hardware minimum is
claimed without a benchmark. Docker build and Azure deployment status are explicitly
reported in deployment/validation documentation.
