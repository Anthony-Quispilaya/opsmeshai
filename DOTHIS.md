# OpsMesh AI — Product Expansion Brief for Claude

## Read this first

You are working on an **existing codebase** that already has important parts connected and functioning.

This is **not** a greenfield rebuild.
Do **not** throw away what already works.
Do **not** rewrite the project from scratch.
Do **not** force old spec-sheet structure back into the codebase if the current architecture has already evolved beyond that.

The current reality is:

- the AI agent is already working
- Photon messaging is already working
- OpenAI API key is loading and working
- the SMS / iMessage-style AI agent is already able to communicate
- the project has shifted from the original planning docs, so older spec sheets are no longer the exact source of truth for implementation
- we now need to build **real product functionality** on top of what is already connected

Your job is to **extend the existing project** into something that feels useful, believable, and impressive to companies.

---

# High-level objective

We want to turn the current system into a **multi-domain AI operations product** that can:

1. display believable operational data on the dashboard
2. let the AI messaging agent add and update data through phone messages
3. support realistic business workflows
4. feel useful for real company scenarios
5. create a stronger hiring signal for roles in:
   - banking / fintech
   - enterprise AI / forward deployed engineering
   - operations automation
   - support / compliance / workflow tooling

This should become a **messaging-first AI workflow system**, where the website is the operations dashboard, but the phone agent is also a primary interface.

---

# Core product direction

The product should evolve into:

## **OpsMesh AI**
A messaging-first, AI-powered workflow and decision copilot that supports:

- banking-style transaction and risk workflows
- support operations workflows
- compliance / policy workflows
- dashboard visibility
- SMS/iMessage-based data input
- AI-driven explanations and summaries

The important product idea is:

> The user should not need to log into the dashboard just to add or report something.
> They should be able to text the AI agent and have the system intelligently create records, update the backend, and reflect those changes on the dashboard.

That is one of the most important additions.

---

# Important implementation mindset

Because you do not know the exact current code structure yet, you must first:

1. inspect the current codebase
2. identify what already exists
3. preserve working integrations
4. extend the current architecture instead of fighting it

You should adapt to the current codebase rather than forcing a totally different architecture.

Before making changes, determine:

- where the messaging webhook currently lives
- how the OpenAI agent is currently invoked
- what database or persistence layer currently exists
- what frontend routes/components already exist
- how data is currently fetched on the dashboard
- whether the project already has server actions, API routes, REST endpoints, or other patterns in use

Then build additions in a way that matches the codebase style.

---

# What we want to add now

We want to add a **realistic data layer** and a **messaging-to-data workflow**.

The biggest new product behaviors should be:

## 1. Seed believable data
We need believable data for the dashboard so the product does not feel empty.

## 2. SMS / iMessage AI can add data
The user should be able to message the AI agent and create records without logging into the site.

## 3. SMS / iMessage AI can query data
The user should be able to ask the agent questions and get useful responses based on stored data.

## 4. SMS / iMessage AI can trigger workflows
The user should be able to ask the agent to analyze activity, summarize issues, or surface risks.

## 5. Dashboard reflects these changes
As data is added or analyzed, the dashboard should show useful insights and tables.

---

# Product use cases we want supported

We want the product to feel like one platform that can support several scenarios.

## Domain 1: Banking / Fintech
Examples:
- spending / transaction records
- potentially suspicious transactions
- risk scoring
- unusual merchant / location / amount activity
- audit trail

## Domain 2: Support Operations
Examples:
- refund issues
- login problems
- payment failures
- ticket volume
- common issue clustering

## Domain 3: Compliance / Policy
Examples:
- expense policy checks
- action approval / rejection
- policy-flagged records
- audit logging

The implementation does not need to be enterprise-perfect, but it must feel like a real operations product.

---

# Most important new feature: AI messaging agent as data-entry interface

This is the key addition.

The AI agent should not just chat.
It should act like an intelligent operational assistant.

## Required behavior

The user can text messages like:

- `Spent 120 at Amazon in NJ`
- `Spent 2400 at Apple in Miami`
- `Customer says refund still not received for order 4832`
- `Payment failed again for user Maria`
- `Check fraud activity`
- `Show me flagged transactions`
- `Summarize today's support issues`
- `Add compliance note: employee booked first class for internal meeting`

The agent should:

1. understand the intent
2. parse structured information
3. write data to the backend/database
4. optionally analyze or summarize
5. return a helpful confirmation

This is extremely important because it creates a strong product story:

> "Users can operate the system directly from their phone without needing to log into the dashboard."

---

# Required capabilities for the AI messaging agent

The messaging agent should support these intent types.

## Intent: Add Transaction
Example messages:
- `Spent 120 at Amazon in NJ`
- `I spent 65 on Uber in New York`
- `Add transaction 1800 at Best Buy in Florida`

Expected outcome:
- create transaction record
- infer category if possible
- assign timestamp
- optionally risk score it
- confirm back to user

Example response:
- `Added transaction: $120 at Amazon in NJ. Risk score: low. Want me to analyze recent spending?`

---

## Intent: Add Support Ticket / Issue
Example messages:
- `Customer reports refund delay for order #1234`
- `Login issue for Sarah, password reset not working`
- `Payment failed for order 9842`

Expected outcome:
- create support record or ticket
- categorize issue
- assign status = open
- confirm record creation

Example response:
- `Support issue recorded as Refund Delay. Ticket status: Open.`

---

## Intent: Add Compliance Record / Note
Example messages:
- `Employee submitted expense for premium seat upgrade`
- `Add compliance note: missing receipt for travel reimbursement`

Expected outcome:
- create compliance-related record
- flag if policy-sensitive
- mark status = pending review
- confirm back to user

Example response:
- `Compliance record added and marked for review.`

---

## Intent: Query Data
Example messages:
- `Show me flagged transactions`
- `How many support tickets are open?`
- `What is the biggest transaction today?`
- `What compliance issues are pending?`

Expected outcome:
- query stored data
- summarize the results
- keep the answer concise but useful

---

## Intent: Trigger Analysis
Example messages:
- `Check fraud activity`
- `Analyze today's transactions`
- `Summarize support problems`
- `What should I worry about today?`

Expected outcome:
- run simple analysis over stored data
- surface anomalies / trends / summaries
- respond in a way that feels like an operations assistant

---

## Intent: Unknown / Clarification
If message cannot be confidently parsed:
- ask follow-up question
- do not silently invent incorrect data

Example:
- `Can you log that weird thing from earlier?`

Response:
- `I can help with that. Was it a transaction, a support issue, or a compliance note?`

---

# Data we need in the system

We need believable, structured seed data so the dashboard has something useful to show even before live SMS input begins.

Create or extend the backend data model to support these entities.

---

# Data model requirements

## Transactions

Each transaction should include at least:

- id
- user or account identifier
- amount
- merchant
- location
- timestamp
- category
- risk_score
- flagged boolean
- notes or reasoning field if useful

Recommended categories:
- groceries
- travel
- electronics
- dining
- transport
- subscriptions
- retail
- transfers
- entertainment
- utilities

Recommended behavior:
- some transactions should be normal
- some should be suspicious
- some should create visible dashboard variety

---

## Support tickets / support issues

Each support item should include at least:

- id
- customer or user identifier
- issue description
- category
- status
- priority
- created_at
- optionally assigned team or source

Recommended categories:
- refund delay
- login issue
- payment failure
- duplicate charge
- verification problem
- account locked
- transfer issue

Recommended statuses:
- open
- in review
- resolved

---

## Compliance records

Each compliance record should include at least:

- id
- record type
- description
- status
- policy_flag boolean
- created_at
- optional severity
- optional recommendation

Recommended examples:
- missing documentation
- suspicious reimbursement
- out-of-policy expense
- manual override recorded
- unusual approval path

---

## Audit logs

Everything important should be logged.

Each audit log entry should include at least:

- id
- event_type
- domain
- action_taken
- reasoning
- created_at
- source (dashboard, sms, system, ai)
- related entity id if applicable

This is important because it makes the system feel more real and enterprise-like.

---

# Seed data requirements

Add believable seed data so the dashboard feels alive.

## Transactions seed data
Create at least **60** transactions.

The dataset should include:
- everyday normal spending
- a few high-dollar anomalies
- a few unusual location changes
- a few transactions late at night
- a few new merchants that feel riskier
- a mixture of flagged and non-flagged items

Examples:
- $14.50 at Starbucks in Jersey City
- $62.00 at ShopRite in Hoboken
- $120.00 at Amazon in NJ
- $2,450.00 at Apple Store in Miami
- $980.00 at Delta Airlines in Newark
- $1,900.00 at Best Buy in Orlando at 2:13 AM
- $15.99 Netflix subscription
- $8.75 MTA transit
- $310.00 Sephora in Los Angeles
- $4,200.00 Luxury Watch Shop in Las Vegas

The goal is not perfect realism but believable operational variety.

---

## Support tickets seed data
Create at least **35** support issues.

Examples:
- refund delay
- duplicate charge complaint
- password reset failure
- transfer pending too long
- card declined unexpectedly
- account verification issue
- suspicious transaction complaint
- app login timeout

We want enough data to:
- show tables
- surface counts
- summarize trends
- make charts useful

---

## Compliance records seed data
Create at least **20** compliance records.

Examples:
- reimbursement missing receipt
- business class upgrade flagged
- suspicious manual override
- transfer approved outside normal path
- expense submitted without documentation

Include a mix of:
- approved
- pending
- rejected

---

## Audit logs seed data
Create enough logs to make the activity feed and audit tables useful.

Examples:
- transaction flagged
- support issue created
- compliance record added
- SMS-created transaction
- AI-generated summary request
- manual review opened

---

# Dashboard improvements we want

The dashboard should become useful immediately.

It should not just be empty cards.
It should show meaningful operational information using seeded data plus live updates from SMS-created data.

## Add overview cards
At minimum include cards for:

- total transactions
- flagged transactions
- open support tickets
- pending compliance items

Optional extra cards:
- average transaction amount
- today's volume
- risk alerts this week
- resolved tickets
- audit events today

---

## Add recent activity / audit feed
Show recent events such as:

- transaction added
- transaction flagged
- support issue opened
- compliance item marked pending
- message received from user
- AI analysis triggered

This helps the product feel alive.

---

## Add transactions table
Include:
- merchant
- amount
- location
- timestamp
- category
- risk score
- flagged status

Support simple sorting or filtering if easy.

---

## Add support issues table
Include:
- issue
- category
- status
- priority
- created date

---

## Add compliance table
Include:
- description
- status
- policy flag
- severity
- created date

---

## Add insights panel
Include AI-generated summaries or derived insights like:
- most common support issue today
- number of flagged transactions this week
- highest-risk transaction
- most common compliance problem
- potential anomaly summary

These can initially be computed heuristically if needed.

---

# Risk scoring / simple intelligence rules

Do not overcomplicate this.
We need believable product behavior, not research-level fraud modeling.

Implement a simple but useful rule-based or hybrid system for transactions.

## Suggested risk signals
Increase risk if:
- amount > 1000
- amount > 2500 even more
- location differs significantly from recent location
- transaction occurs at unusual hour
- merchant appears new or uncommon
- category is electronics / luxury / travel at high amount
- rapid transaction burst occurs

Use a simple numeric risk score, such as:
- 0–30 low
- 31–70 medium
- 71–100 high

Then set:
- flagged = true if score crosses threshold

If AI reasoning is used, log its explanation or summary.

---

# What the SMS / iMessage agent must do technically

The phone agent must be able to create data entries without dashboard login.

That means the system should support a flow like:

1. user sends message
2. webhook receives message
3. system classifies intent
4. system parses message into structured fields
5. system stores data in backend/database
6. system optionally triggers analysis
7. system sends confirmation response
8. dashboard reflects new data

This should be treated as a first-class workflow.

---

# Intent classification requirements

Implement or extend intent detection for messages.

At minimum support:

- ADD_TRANSACTION
- ADD_SUPPORT_TICKET
- ADD_COMPLIANCE_RECORD
- QUERY_DATA
- RUN_ANALYSIS
- UNKNOWN

Use either:
- structured prompting with the model
- rule-based shortcuts for common patterns
- or a combination of both

Prefer robust and simple behavior over overengineering.

---

# Message parsing requirements

The system should attempt to parse messages into structured records.

## Transaction parsing examples

Input:
- `Spent 120 at Amazon in NJ`
- `I paid 48 for dinner in Hoboken`
- `Add transaction 2499 at Apple in Miami`

Desired parsed fields:
- amount
- merchant
- location
- maybe category if inferable
- timestamp = now unless otherwise specified

If a field is missing, ask a short follow-up.

Example:
- `Added the merchant and amount. What location should I use?`

---

## Support issue parsing examples

Input:
- `Customer reports refund delay for order #1234`
- `Login issue for user Maria`
- `Payment keeps failing for customer James`

Desired parsed fields:
- issue description
- category
- maybe customer identifier if present
- status default = open

---

## Compliance parsing examples

Input:
- `Employee submitted first class flight reimbursement`
- `Missing receipt for travel expense`
- `Add compliance note: premium meal expense not justified`

Desired parsed fields:
- description
- type
- status default = pending
- policy_flag true if it seems sensitive

---

# Query behavior requirements

The agent should be able to answer questions from stored data.

Examples:
- `How many flagged transactions today?`
- `Show open tickets`
- `What is the highest risk transaction?`
- `Any compliance issues pending?`
- `What are the most common support issues?`

The response should be:
- concise
- useful
- based on real stored data
- not hallucinated

If helpful, include counts, merchants, issue categories, or short highlights.

---

# Analysis behavior requirements

The agent should be able to do basic analysis and summarize it in plain language.

Examples:
- `Check fraud activity`
- `Analyze today's transactions`
- `Summarize support trends`
- `What needs attention right now?`

Examples of good responses:
- `There are 4 high-risk transactions today. The largest is $2,450 at Apple Store in Miami. Two flagged events happened outside the user's normal location pattern.`
- `Refund delay is the most common support issue today with 8 open tickets.`
- `There are 3 pending compliance records and 2 were flagged as out-of-policy.`

This will make the AI feel useful instead of generic.

---

# Dashboard sync requirements

New records created through SMS should appear on the dashboard without needing manual website entry.

If the current stack supports realtime or polling, use the pattern already present in the codebase.
If not, implement the cleanest existing pattern available.

The important thing is:
- if user sends message on phone
- new record gets stored
- dashboard reflects the update

This product behavior is one of the strongest parts of the demo.

---

# UI / UX expectations

Do not redesign the entire app unless necessary.
Respect the current UI direction.

But improve the dashboard so it feels more complete and believable.

The dashboard should feel:
- modern
- clean
- readable
- data-driven
- operational

Avoid:
- giant empty spaces
- placeholder-only cards
- inconsistent styling
- random colors
- cluttered layouts

Prefer:
- clear cards
- tables with useful data
- concise labels
- meaningful activity feed
- simple charts only if they genuinely help

---

# Suggested feature areas to implement now

## Priority 1
- seed data
- dashboard populated with believable info
- SMS/iMessage create transaction
- SMS/iMessage create support issue
- SMS/iMessage create compliance record

## Priority 2
- query data through messaging
- run analysis through messaging
- recent activity feed
- risk scoring

## Priority 3
- charts / small visualizations
- filters
- better summaries
- more advanced parsing

---

# Constraints

## Do not do these
- do not rebuild entire app from scratch
- do not delete existing working messaging logic
- do not replace working AI plumbing unless necessary
- do not overengineer a huge framework before adding value
- do not add fake complexity with no visible benefit

## Do these
- preserve working flows
- inspect current architecture first
- extend incrementally
- make features visible in the UI
- make the phone agent actually useful
- keep the data believable
- keep the code modular and maintainable

---

# What success looks like

A successful implementation means:

## On the phone
The user can text:
- `Spent 120 at Amazon in NJ`
- `Customer reports refund delay for order #1234`
- `Add compliance note: missing receipt for flight`
- `Check fraud activity`
- `How many open tickets?`

And the system:
- understands the message
- writes or queries real backend data
- returns useful responses

## On the dashboard
The user can see:
- believable cards and totals
- tables with seeded + live data
- flagged items
- recent activity
- summaries and insights

This should feel like an actual product demo, not a blank prototype.

---

# Implementation instructions

Please do the following in order:

## Step 1 — Inspect and summarize current project
Before writing a lot of code, inspect the codebase and summarize:
- current frontend structure
- current backend / API structure
- current messaging integration location
- current data layer / persistence
- where best to extend functionality

## Step 2 — Identify safest extension points
List where you will plug in:
- data models
- seed logic
- intent classification
- message parsing
- database writes
- dashboard queries

## Step 3 — Implement the new data layer
Add or extend:
- transactions
- support tickets
- compliance records
- audit logs

## Step 4 — Add believable seed data
Populate the system with enough data to make the dashboard useful immediately.

## Step 5 — Extend messaging workflow
Allow SMS/iMessage messages to:
- add records
- query records
- trigger analysis

## Step 6 — Update dashboard
Show:
- overview cards
- tables
- recent activity
- insights

## Step 7 — Explain what changed
After implementation, clearly explain:
- files changed
- new flows added
- how to test the new message commands
- how seeded data appears
- how dashboard reflects new records

---

# Testing requirements

After implementation, I should be able to test flows like:

## Transaction add flow
Message:
`Spent 120 at Amazon in NJ`

Expected:
- transaction stored
- confirmation sent
- dashboard count updates
- transaction appears in recent table

## Support issue add flow
Message:
`Customer reports refund delay for order #1234`

Expected:
- support record created
- category inferred
- open issue count updates

## Compliance add flow
Message:
`Add compliance note: employee submitted premium flight upgrade`

Expected:
- compliance record created
- flagged for review if appropriate
- dashboard updates

## Query flow
Message:
`How many flagged transactions today?`

Expected:
- answer based on real stored data

## Analysis flow
Message:
`Check fraud activity`

Expected:
- useful risk summary returned

---

# Optional nice-to-have additions if time allows

- ability to edit or update a record through SMS
- simple confirmation step for ambiguous inputs
- ability to tag the source of data entry as `sms`
- simple charts for transaction volume or support category distribution
- lightweight command help message such as:
  - `Try: "Spent 45 at Starbucks in NYC"`
  - `Try: "Show open tickets"`
  - `Try: "Check fraud activity"`

---

# Final output expectations

When you respond after implementation, provide:

1. a summary of what you found in the current codebase
2. the architecture choices you made
3. the files you changed
4. the main code additions
5. the supported SMS/iMessage commands
6. how the seeded data works
7. how to test everything manually

---

# Final note

The most important thing is not abstract architecture.
The most important thing is visible product value.

This should feel like:

> an AI operations product where the phone agent is a real input interface and the dashboard becomes the system of record and visibility

Build toward that.

Start by inspecting the current codebase and extending it safely.