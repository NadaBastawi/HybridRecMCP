# Verified evaluation results

Local verification: 21 October 2026, Python 3.12.3, locked NumPy 2.4.4 / pandas 3.0.2 / scikit-learn 1.8.0. Synthetic data only. The full report reproduced exactly on a second run.

## Protocol

One hundred customers are reserved by a deterministic SHA-256 ordering seeded with 42 before any fit. All their records and profiles are excluded from model/transform fitting and tuning. Warm bookings are split by global complete-date boundaries. Each customer receives a single frozen ranking query at 2025-05-21; future-window distinct completed bookings are the relevant set. Repeat bookings remain eligible.

| Partition | Interactions | Dates / sample notes |
|---|---:|---|
| Warm training | 1,478 | Through 2024-10-14 |
| Warm validation | 470 | 2024-10-15 through 2025-05-20 |
| Warm test | 452 | From 2025-05-21; 298 customers |
| Cold test | 104 | Same future window; 67 of 100 reserved customers have bookings |

Validation NDCG selects among content weights 0, 0.4, 0.7, 1.0 and SVD ranks 2, 3. Test data selects nothing. The final evaluation model fits the 1,948 warm train+validation interactions only. Deterministic ties favor the first candidate. Selected weights: **content 100%, collaborative 0%; SVD rank 2**. This dataset does not support claiming the 40/60 blend is superior. The deployment artifact is separately fitted on all synthetic data, including cold-test profiles, after evaluation; its predictions are not used to score the reported holdout.

## Warm ranking

| Method | HitRate@5 | Precision@5 | Recall@5 | NDCG@5 | Catalog coverage |
|---|---:|---:|---:|---:|---:|
| Validation-selected (content only) | 0.8087 | 0.2007 | 0.7209 | 0.4704 | 100% |
| Fixed 40/60 hybrid | 0.7617 | 0.1832 | 0.6544 | 0.4447 | 100% |
| Collaborative only | 0.6913 | 0.1611 | 0.5761 | 0.3920 | 100% |
| Content only | 0.8087 | 0.2007 | 0.7209 | 0.4704 | 100% |
| Popularity | 0.8087 | 0.2054 | 0.7170 | 0.4921 | 50% |
| Illustrative profile rule | 0.8591 | 0.2242 | 0.7897 | 0.5521 | 90% |

Popularity exceeds the selected model on precision and NDCG, while the content model covers more of the catalog. The profile-rule baseline performs best here and shares assumptions with the generator. These are honest comparisons, not evidence of business lift.

## Cold-start ranking

| Method | HitRate@5 | Precision@5 | Recall@5 | NDCG@5 | Catalog coverage |
|---|---:|---:|---:|---:|---:|
| Content only | 0.7761 | 0.2000 | 0.7015 | 0.4578 | 100% |
| Popularity | 0.7761 | 0.2060 | 0.7065 | 0.4905 | 50% |
| Illustrative profile rule | 0.8358 | 0.2239 | 0.7811 | 0.5429 | 90% |

Cold-start ranks profile affinity, with no personal history and no urgency-based relevance ordering. The same full ten-item catalog is the coverage denominator; eligibility applies per customer.

## Metric definitions

- HitRate@K: fraction of evaluated customers with at least one relevant recommendation.
- Precision@K: relevant returned items divided by K, averaged across customers.
- Recall@K: relevant returned items divided by the number of distinct held-out booked services, averaged across customers.
- NDCG@K: binary discounted gain, with gain 1/log2(rank+1), normalized by the ideal ranking of min(K, number of relevant services) hits.
- Catalog coverage: distinct service IDs recommended across evaluated customers divided by ten catalog services. It does not measure staff acceptance or usefulness.

## Urgency (separate task)

The 452 warm held-out events condition on each actual service, season and elapsed visit gap. This is not a test-window-start forecast. Targets come from an illustrative rule with bounded integer noise.

| Estimator | MAE | RMSE |
|---|---:|---:|
| Gradient Boosting | 0.7508 | 0.8699 |
| Rule Baseline | 0.6814 | 0.8255 |
| Training Mean | 1.2018 | 1.4871 |

The generator-aware rule beats the learned model; learning noisy rules does not establish environmental or operational risk accuracy. Neither model estimates a validated treatment deadline.

## Limitations

- Synthetic data only; no evidence of real customer benefit.
- Profile and urgency rule baselines share simulator assumptions and have privileged knowledge.
- Only ten services; top-five hit rate is inherently generous.
- Unbooked services are unobserved, not confirmed irrelevant.
- No causal lift, calibrated confidence, or professional pest-risk validation.
- One fixed split and seed; uncertainty intervals and broader stability studies remain future work.
- The 33 reserved customers with no future-window booking cannot receive a booked-service ranking label and are not counted.
- Coarse static property profiles and hand-authored suitability need expert review. No real company record, price, outcome, authorization or financial benefit is established.

## Reproduce

```sh
python generate_data.py
python evaluate.py
python train.py
```

`python -m pytest tests/test_evaluation.py` verifies known-answer metrics, date boundaries, exact fit isolation and small-fixture reproducibility. Full-dataset CSVs/manifest were independently regenerated byte for byte, and a second full evaluation JSON matched exactly. The original 96.2% Precision@5 claim is withdrawn.
