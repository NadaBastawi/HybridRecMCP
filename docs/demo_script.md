# Demonstration script — 3–5 minutes

## Before the meeting

For a short public presentation use the [60–90 second flow](public_demo_checklist.md).
For local rehearsal install `requirements-demo.txt`, then
launch `python -m streamlit run demo.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false`.
Open localhost:8501. Rehearse without a network connection after dependencies are installed.
Use the supplied synthetic dataset only. Confirm which business you are speaking with;
do not assume similarly named Tucson and Ohio organizations are related.

## 0:00–0:35 — Introduction and context

“I'm Nada Bastawi. I independently built this proof of concept to show how an AI-enabled
review assistant could help a pest-control service team. This is my portfolio work,
not a commissioned or endorsed company system. Every customer and price on screen is
simulated.”

## 0:35–1:00 — The staff question

“The question I'm exploring is: given a property's characteristics and previous service,
which options might staff discuss next, and which follow-ups deserve attention? The
assistant organizes possibilities; staff still confirm the facts and make decisions.”

## 1:00–2:00 — New customer example

Choose New customer, Tucson, residential house, ZIP 85743, building age 30, summer,
Unknown service timing. Click Explore relevant services. Priority stays unknown until
a known interval is entered; do not invent 400 days for a new customer.

“Here's a homeowner without a recorded service history. The system uses the property
profile to suggest a short list. The order reflects relevance; the separate priority
label is separate and remains unknown here. The staff question helps confirm actual
observations. These prices are examples, not company
quotes. Nothing here establishes an infestation or authorizes a treatment.”

Read the actual top result rather than promising a fixed service order. Optionally
switch to Ohio and ZIP 43215: explain that this is a separate demonstration catalog,
not another branch of the same business. Note the scorpion service is out of scope there.

## 2:00–2:45 — Existing synthetic customer

Choose Existing synthetic customer, C0001, then Explore relevant services.

“Now we have simulated history as well as a profile. The engine supports using both.
Check the technical section for the selected weights: if personal-history weight is
zero, validation favored profiles on this dataset and I am not claiming personalized
history improves the result. Staff could review the ideas, ask what the customer has
observed, and decide whether a follow-up or inspection is appropriate.”

## 2:45–3:20 — How it works and MCP

“Behind the screen, the system compares property profiles and patterns in previous
visits. Priority is estimated separately. I also implemented an authenticated API and
MCP tools, so a future authorized AI assistant could retrieve these suggestions.”

Example future prompt: “Show service ideas for synthetic customer C0001 this summer;
explain the limitations and flag the prices as illustrative.”

“The current tools retrieve suggestions. They do not book appointments, contact
customers or connect to a company CRM.”

## 3:20–4:15 — Engineering and limitations

“There's automated testing of the API, real MCP client communication, data quality and
the presentation screen. I corrected the original evaluation to keep future bookings
out of training and compared it with simple baselines. The published numbers describe
only this synthetic task; they do not demonstrate customer benefit or financial return.
The priority model is learning illustrative rules, not professionally validated risk.”

## 4:15–4:45 — Proposed next step

“If this review workflow is useful, I'd suggest a small discovery exercise: agree on
the service catalog and staff process, review suitability rules with a specialist,
and decide what authorized historical data and measures would support a pilot. I'd be
interested in discussing how I could contribute as an engineer or project collaborator.”

Do not improvise claims of partnership, production deployment, percentage savings or
verified infestation risk. If asked about deployment, distinguish local verification
from an actually verified public Streamlit URL, external Azure configuration and the
unverified Docker build. Publishing is still pending; do not share a localhost address.
