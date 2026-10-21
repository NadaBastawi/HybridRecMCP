# Regional assumptions and public context

Tucson, Arizona is the default public API/UI scenario. Ohio is a separately labeled
illustration. No claim is made about company identity, ownership, actual service areas,
pricing, endorsement or relationships between similarly named businesses. Verify the
intended company independently before any outreach; this repository contacts nobody.

## Public context (consulted 21 October 2026)

- [University of Arizona Community IPM: Scorpion Season is Here](https://acis.cals.arizona.edu/community-ipm/home-and-school-ipm-newsletters/ipm-newsletters/2025/05/16/scorpion-season-is-here!) discusses low-desert activity and warm nighttime conditions. This supports including a seasonal Arizona illustration; it does not establish ZIP-level risk.
- [University of Arizona Extension: Termite Management, AZ1356](https://extension.arizona.edu/sites/extension.arizona.edu/files/pubs/az1356.pdf) describes species-specific activity, including monsoon-associated flights. The project's broad spring/summer setting is a simplification and not a measured local risk curve.
- [University of Georgia Extension: Biology of Subterranean Termites in the Eastern United States](https://extension.uga.edu/publications/detail.html?number=B1209) provides general eastern-US biology; it is not an Ohio company or ZIP-level dataset.
- [University of Georgia IPM: Subterranean termites](https://ipm.uga.edu/2026/02/10/subterraneantermites/) describes spring swarming while noting possible activity at other times. The Ohio spring scenario is an illustrative extrapolation from broad eastern-US context, not an Ohio prevalence estimate.

## Deliberate simulation choices

`config/regions.json` centralizes example ZIPs, broad prefixes, seasonal settings and
whether the scorpion service is in the demonstration catalog. Tucson example ZIPs and
Ohio example ZIPs merely label scenarios. The desert-scenario ZIP list is an arbitrary
illustration, not validated adjacency, infestation data or demographic research.
Broad prefixes are only a demo support indicator, not a postal/geocoding validator or
company service-area check. Unknown five-digit ZIPs are accepted with a limited-location
explanation. They are not silently assigned an observed local risk.

All service probabilities, prices, property mix, age thresholds, priority weights and
repeat patterns are hand-authored. Building age alone is not proof of infestation.
Commercial/residential compatibility is a conservative catalog rule requiring expert
review. Ohio's omission of scorpion service is a scope choice, not a biological absence
claim. No claims about health effects or treatment necessity are made.
