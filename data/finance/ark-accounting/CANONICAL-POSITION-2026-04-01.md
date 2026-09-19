# Canonical Financial Position
**As of: 2026-04-14**
**Status: CURRENT -- this is the single source of truth**

All prior spreadsheet data (raw_sheet.json, debts.csv, cost_items.csv, balance_updates_staging.csv, assets_working.csv) is HISTORIC. Reference this file first. Update this file when numbers change. Do not reconstruct from the spreadsheets.

---

## Liquid

| Account | Balance |
|---------|---------|
| Barclays current | 1,984.09 |
| Monzo Business | 1,820.41 |
| Barclays Savings | 0.56 |
| **Total cash** | **3,805.06** |

Pending:
- eBay payouts: £472 (X1 Carbon £432 + Mac Mini £40)
- Aurora R9 eBay sale: ~475 (listed, unsold)

Projected liquid after pending payouts: ~4,277
Projected liquid after all remaining sales: ~5,487

## Debt

| Creditor | Balance | APR | Monthly interest | Min payment | Account ref | Notes |
|----------|---------|-----|-----------------|-------------|-------------|-------|
| Virgin credit card | 11,379.61 | 26.49% | ~131 (current) | 166.62 | 5276 6900 9303 1114 | Balance: £2,209 purchases + £3,744 BT (0% expired 31/03) + £5,594 BT (0% until 31/05). £5,953 now at 26.49%. March statement showed £51.67 (pre-expiry). Post-June: full balance at 26.49% = ~£255/mo. |
| Iwoca loan | 6,156.25 | ~37% | ~194 | 193.83 (Apr) | 6U33E2W7N2WD2 | Interest-only until June. Jumps to 622.19/mo from June (P+I). Personal guarantee on OCEANHEART.AI LTD loan. Principal unchanged at £6,150 — payments are pure interest. |
| MBNA Loan 2 | 5,016.81 | ~15% | ~66 | 306.82 | 100215088397 | Fixed self-amortising payment. Balance confirmed from MBNA app. |
| AMEX business card | 3,210.94 | 30.5% | ~67 | 154.59 | 3773 9342 30 51006 | Amazon Business AMEX. Credit limit £4,300. Post-returns, post-M5-keep. |
| MBNA credit card | 3,810.46 | 26.32% | ~69 | 159.98 | 5230 6700 4546 4550 | Revolving. Effective rate 26.32% (simple 23.6%). Balance UP from 3,701 — interest accrual. |
| Capital On Tap | 3,365.23 | ~34% | ~96 | 336.52 | X728K69 (card *7665) | Business credit card. Monthly rate 2.86% on purchases. OCEANHEART.AI account. |
| M3 Max (Klarna) | 441.78 | 0% | 0 | 160.00 | — | Nearly done. ~3 payments left. |
| **Total debt** | **~33,381** | | **~623/mo** (current) | | | Post-June (all Virgin promos expired): **~747/mo** |

## Hardware Decisions (committed 2026-04-01)

| Item | Action | Value | Status |
|------|--------|-------|--------|
| PS5 | SOLD | 350 cash | Done |
| 64GB mini (Amazon) | RETURNED | -869 off AMEX | Done. |
| M5 MacBook Air (Amazon) | KEEPING | -- | X1 Carbon wifi/BT unreliable on Arch. M5 is primary machine. 1,384 stays on AMEX. |
| Aurora R9 | SELL (eBay) | ~380 asking (reduced from 475) | Listed 2026-04-02. Collection only. |
| ThinkPad X1 Carbon 9th Gen | SOLD | 432 (balance with eBay) | Sold. Awaiting eBay payout. |
| ThinkPad X230 i5 16GB | SELL (eBay) | ~170 asking | Listed 2026-04-02. |
| Lenovo Legion Y27q-25 240Hz | SELL (eBay) | ~123 asking (reduced from 200) | Listed 2026-04-02. Collection only. |
| Mac Mini 5 (2011) | SOLD | 40 (balance with eBay) | Sold. Awaiting eBay payout. |

Sold so far: PS5 (350 received), X1 Carbon (432 with eBay), Mac Mini (40 with eBay) = 822 total (350 received, 472 pending eBay payout).
Remaining listings: Aurora R9 (~380), X230 (~170), Legion monitor (~123) = ~673 asking.
Total hardware realised + pending: 822. If remaining sell at asking: ~1,495. Realistic net on remaining (fees + negotiation): ~500-550.
Nipogi 32GB mini: removed from sale — hosting Kubernetes work.

## Monthly Burn (actual)

### Living: ~1,213/mo (StepChange-assessed, adjusted 14 Apr)

StepChange budget is the baseline. Adjusted: professional fees reduced, courses removed, toiletries reduced, buffer added.

| Category | Monthly | Source |
|----------|---------|--------|
| Groceries | 500.00 | StepChange (health/medical condition flag) |
| Prescriptions and medicine | 200.00 | StepChange |
| Professional fees | 170.00 | StepChange (compute, software, hosting) — reduced from 350 on 14 Apr |
| Buffer | 100.00 | General contingency |
| Mobile phone | 65.00 | StepChange (contract penalty for early termination) |
| Toiletries | 50.00 | Reduced from 100 on 14 Apr |
| Clothing and footwear | 41.67 | StepChange |
| Hobbies, leisure or sport | 35.00 | StepChange |
| Home phone, internet and TV | 30.00 | StepChange |
| Gifts | 20.83 | StepChange |
| **Living total** | **~1,213** | StepChange base (13 Apr), adjusted 14 Apr |

### Debt service: ~1,477/mo (current, pre-June)

| Creditor | Payment | Type |
|----------|---------|------|
| Capital On Tap | 336.52 | Min (P+I) |
| MBNA Loan | 306.82 | Fixed (self-amortising). Only MBNA loan — prior loan paid off in full before these sessions. |
| Iwoca (Apr/May) | 193.83 | Interest only |
| Virgin | 166.62 | Min (statement confirmed) |
| Klarna M3 Max | 160.00 | Principal only (0%) |
| MBNA credit card | 159.98 | Min (statement confirmed) |
| AMEX | 154.59 | Min (statement confirmed) |
| **Debt service total** | **~1,479** | |

### Total burn: ~2,692/mo (current, pre-June)

### June step-up: Iwoca jumps from ~194 to 622/mo
- Debt service rises to ~2,031/mo
- Total burn rises to ~3,244/mo
- Virgin last 0% promo on £5,594 also expires 31/05/2026 — interest jumps from ~£131/mo to ~£255/mo
- Combined June shock: +£428 (Iwoca) + ~£124 (Virgin second promo lapse) = **+£552/mo**

## Interest Summary

### Current (Apr 2026, one Virgin promo expired, one active)

| Creditor | APR | Monthly interest | Source |
|----------|-----|-----------------|--------|
| Iwoca (37%) | ~37% | ~194 | Statement (interest-only payments) |
| Virgin (26.49%) | 26.49% | ~131 | Calculated: £5,953 at 26.49% (£3,744 BT promo expired 31/03 + £2,209 purchases). £5,594 BT still at 0% until 31/05. March statement showed £51.67 (pre-expiry). |
| Capital On Tap (34%) | ~34% | ~96 | Calculated (2.86% monthly on £3,365) |
| AMEX (30.5%) | 30.5% | 71.02 | Statement |
| MBNA credit card (26.3%) | 26.32% | 67.44 | Statement |
| MBNA Loan 2 (15%) | ~15% | ~66 | Estimated |
| Klarna | 0% | 0 | — |
| **Total interest** | | **~625/mo** | |

### Post-June (all Virgin promos expired, Iwoca unchanged)

| Creditor | Monthly interest |
|----------|-----------------|
| Virgin (full balance at 26.49%) | ~255 |
| Iwoca | ~194 |
| Capital On Tap | ~96 |
| AMEX | ~71 |
| MBNA credit card | ~67 |
| MBNA Loan 2 | ~66 |
| Klarna | 0 |
| **Total interest** | **~749/mo** |

Of the ~2,692/mo going out, ~625 is pure interest (current). Rises to ~749 post-June.

## Runway

| Scenario | Months to zero | Date |
|----------|---------------|------|
| At current burn (2,692/mo) | ~1.4 | Late May 2026 |
| At June burn (3,244/mo) | ~1.2 | Late May 2026 |
| **If full suspension holds** (1,213/mo) | ~3.1 | Mid-July 2026 |
| If suspension + eBay payouts land (£472 pending) | ~3.5 | Late July 2026 |

**Updated 14 April 2026.** Cash: £3,805. Plus £472 pending eBay payouts.

Corrections baked in:
1. Living costs £1,213 (StepChange base £1,403; professional fees -£180, toiletries -£50, courses -£60, buffer +£100 — adjusted 14 Apr)
2. MBNA Loan: £306.82/mo fixed (only MBNA loan — prior loan paid off before these sessions. Debt service total: £1,479)
3. June shock: Iwoca +£428 AND Virgin second promo lapse +£124 = +£552/mo

## The Conversation (parent briefing)

"Right now I'm spending about 2,900 a month. 1,400 is living costs. 1,500 is debt payments. Of that 1,500, about 550 is pure interest — but that jumps to 750 after June when Virgin promos expire.

In June it gets worse. Iwoca repayments jump from 194 to 622, and Virgin loses its 0% rate on 5,600. Monthly burn goes to 3,300.

I've sold the PS5, I'm returning the new machines to Amazon, and listing the gaming PC. That clears about 1,600. I'm keeping a laptop and a desktop — both already paid for.

At current cash of 5,800, that's about one month before I hit my safety buffer. Without income by mid-May, the maths stops working.

Pipeline is active."

## Outstanding Data Gaps

1. ~~**MBNA Loan 2 account number**~~: RESOLVED — 100215088397, balance £5,016.81, fixed payment £306.82/mo (self-amortising).
2. ~~**AMEX minimum**~~: RESOLVED — £154.59 (statement 6 Mar - 5 Apr 2026)
3. ~~**Virgin promo**~~: RESOLVED — 26.49% standard. Two 0% promos: £3,744 expired 31/03, £5,594 expires 31/05/2026. Not 35%.
4. ~~**MBNA credit card minimum**~~: RESOLVED — £159.98 (statement 24 Mar 2026)
5. ~~**AMEX full account number**~~: RESOLVED — 3773 9342 30 51006 (from card)
6. ~~**MBNA CC full account number**~~: RESOLVED — 5230 6700 4546 4550 (from card)
7. **MBNA Loan 2 account/agreement number**: no card, no statement, no agreement doc provided. Check MBNA online banking or original loan agreement letter.

Fill gap 1 and update this file. Do not go back to the spreadsheets.

---

*Previous data sources (raw_sheet.json, debts.csv, cost_items.csv, balance_updates_staging.csv, assets_working.csv, debts_working.csv) are HISTORIC as of this date. They may contain stale balances and incomplete debt entries. This file supersedes all of them.*

---

## StepChange Assessment (2026-04-07)

Completed online StepChange debt assessment. Results:

### Recommended

- **Payment Suspension** — voluntary agreement with creditors to pause non-priority debt payments for a short period. Recommended option.

### Available but not recommended

- **DRO (Debt Relief Order)** — available. Writes off all debts after 12-month moratorium. No fee (£90 fee abolished 6 April 2024; StepChange PDF confirms "no fee to pay"). StepChange did not recommend; reason given: "You don't have enough money left over in your budget" (contradictory — deficit budget is a DRO qualification criterion, not a disqualifier). To be clarified via follow-up call.
- **Bankruptcy** — available. Writes off all debts. 680 fee. Not recommended by StepChange.

### Not available

- **DMP** — no surplus in budget
- **IVA** — creditors unlikely to accept (paying too little)
- **Settlement offers** — asset value too low
- **Monthly payment arrangement** — no surplus in budget
- **Administration order** — debt too high, no CCJ, no surplus

### Mental health disclosure

StepChange flagged mental health pathway. Diagnosed: bipolar type II NOS (cyclothymia), GAD with compulsive traits. Medications: fluoxetine 40mg OD, lamotrigine 200mg, pregabalin 300mg BD. Mental Health Breathing Space (statutory, not voluntary) may be available — requires mental health professional certification. Materially different from payment suspension: creditors legally required to freeze interest/charges/enforcement for 30 days, renewable indefinitely during treatment.

### Agreed decision sequence (2026-04-07)

1. **Immediate:** Call StepChange mental health line (0333 252 4124). Ask two questions: (a) does Mental Health Breathing Space apply, (b) does mental health context change DRO recommendation.
2. **Primary play:** Mental Health Breathing Space (ruled out by Conner — requires crisis-level presentation). Fallback: Payment Suspension. If all creditors accept, burn drops from ~2,880/mo to ~1,403/mo (living only). Runway extends to ~3.7 months from today.
3. **Backstop:** Bankruptcy. File BEFORE June if Breathing Space fails or creditors refuse. Iwoca step-up in June adds 428/mo — filing before June means never paying it.
4. **Employment remains the structural exit** but is not the plan. It is the upside scenario.

### Bankruptcy scenario analysis

| Factor | Detail |
|--------|--------|
| Cost | 680 (affordable from current liquid) |
| Debt eliminated | ~34,273 |
| Interest eliminated | ~546/mo (current), ~749/mo (post-June) permanently |
| Post-bankruptcy burn | ~1,213/mo (living only) |
| Runway post-bankruptcy to zero | ~2.6 months from ~3,125 (3,805 - 680) |
| Credit impact | 6 years on file. Prior bankruptcy on record. |
| Employment impact | Cannot be company director during bankruptcy. Target roles (senior full-stack, remote) almost certainly unaffected. |
| Asset risk | Trustee reviews assets. M5 MacBook likely exempt as work tool. Cash above "reasonable needs" may be claimed. |
| What it does not cost | Skills, pipeline, agency prospects, earning ability, MacBook (probably) |

### Key insight

At 146 applications with no offer, probability of employment within runway is uncertain. Every day without income costs 96/day burn + 18/day pure interest = 114/day (current; rises to 110/day burn + 25/day interest = 135/day post-June) to preserve a credit score not needed for stated life trajectory (digital nomad, no mortgage, agency via business account). The arithmetic favours insolvency over hope.

## StepChange Call with Conner (2026-04-07, 19:50)

Recording transcribed: `/tmp/stepchange-transcript/19-50-57.txt`

### Bankruptcy — answers received

1. Family paying bills directly on your behalf during bankruptcy: OR has no claim. Money paid into YOUR account: must be negotiated with OR.
2. Surplus income threshold for IPA: must be negotiated with OR. StepChange cannot advise on specifics.
3. DRO and IPA risk: same answer — StepChange cannot confirm whether DRO carries same IPA exposure.
4. Mental Health Breathing Space: effectively unavailable for this situation. Requires crisis-level MH presentation. Not pursued.

### Decision: Payment Suspension

Proceeding with payment suspension. Mechanism:
- Download Personal Action Plan PDF from StepChange dashboard
- Email to all creditors
- Request 6-12 month suspension of payments
- Voluntary on creditor side, but StepChange backing gives weight
- Freezes collections, further processing, and interest accrual (if creditor agrees)

### Collections escalation ladder (from Conner, A-Z)

1. 1-3 missed payments: letters and reminders
2. Creditor sells debt to collection company + default notice (6 years on credit file, 14 days to respond)
3. Collection companies: easier to deal with — debt bought cheap, accept small payments for long periods, all profit
4. If no arrangement: pre-action protocol letter → County Court Judgement (6 years on credit file)
5. Beyond CCJ: attachment of earnings, bailiffs, charging orders on property (N/A — no property owned)

### Fallback if suspension expires without income

- Offer £1/month goodwill gesture to each creditor
- Creditors may sell debt to collection companies at that point
- Collection companies negotiate from a weaker position (bought debt at discount)
- Reassess insolvency options from a position with no surplus income for OR to claim

### Next actions

1. Download Personal Action Plan PDF from StepChange dashboard — TONIGHT
2. Email PDF to all creditors — TOMORROW
3. If income arrives during suspension: call StepChange, redo budget, assess long-term solutions
4. If no income by suspension end: £1/month offers, let process run, reassess insolvency
5. Conner offered follow-up calls as needed: 0800 048 1004

---

## Creditor Response Log

### Iwoca — REFUSED (14 April 2026)

Contact: Jordan Hart, Collections & Recoveries Advisor (jordan.hart@iwoca.co.uk, 020 3778 0173)

- **No payment holidays.** Policy, not negotiation. Iwoca does not offer suspension.
- **No interest freeze.** £194/mo interest-only continues accruing.
- **Asked what funding was used for.** Collections-level question — building a file. Business loan (OCEANHEART.AI LTD), funded February 2026.
- **Late payments register on company credit file** (OCEANHEART.AI LTD, not personal). Personal guarantee bridges them.
- **Escalation:** Breathing Space is available but StepChange advises holding it in reserve for enforcement scenarios (bailiffs, CCJs, eviction). Not recommended to spend it now on a 60-day freeze when voluntary suspension could cover 6-12 months.
- **StepChange cannot advise on Iwoca.** Business debt — referred to Business Debtline (see § StepChange Eligibility Split below).

Impact: £194/mo debt service continues (rises to £622/mo from June). If all other creditors accept suspension but Iwoca refuses, burn is ~£1,597/mo (current) or ~£2,025/mo (post-June) vs ~£1,403/mo if all accept.

### Capital On Tap — Awaiting response (email sent 13 Apr)
- **Business debt (OCEANHEART.AI LTD).** Same eligibility issue as Iwoca — StepChange cannot advise. Needs Business Debtline.

### AMEX — Awaiting response (email sent 13 Apr)
- Amazon Business AMEX. May be classified as business debt — needs clarification on whether personal guarantee makes it StepChange-eligible or Business Debtline territory.

### MBNA credit card — 30-day web suspension active. Call needed for extension.
### MBNA Loan 2 — Email TODAY (14 Apr)
### Virgin — Email TODAY (14 Apr)
### Klarna — Low priority (0%, 3 payments left)

---

## StepChange Eligibility Split (14 April 2026)

**StepChange cannot advise on business debt.** Call on 14 April revealed eligibility boundary: Kai is/was director of OCEANHEART.AI LTD and has business debts. StepChange handles personal debt only. Business debts referred to **Business Debtline** (0800 197 6026).

| Creditor | Balance | Debt type | Advisor |
|----------|---------|-----------|---------|
| Iwoca | 6,156 | Business (OCEANHEART.AI LTD, personal guarantee) | Business Debtline |
| Capital On Tap | 3,365 | Business (OCEANHEART.AI LTD) | Business Debtline |
| AMEX | 4,045 | Business card — classification TBC | Needs clarification |
| Virgin | 11,546 | Personal | StepChange |
| MBNA credit card | 3,701 | Personal | StepChange |
| MBNA Loan 2 | 5,017 | Personal | StepChange |
| Klarna | 442 | Personal | StepChange |

**Personal debt (StepChange):** ~£20,706 — Virgin, MBNA CC, MBNA Loan 2, Klarna
**Business debt (Business Debtline):** ~£9,521 (+ possibly AMEX £4,045) — Iwoca, Capital On Tap

**Key nuance (from advisor):** If OCEANHEART.AI LTD is dissolved, business debts with personal guarantees become personal debts. StepChange can then handle them. This is relevant to both the suspension strategy and Canonical B (bankruptcy).

**Breathing Space — held in reserve.** Advisor confirmed it's available but recommended keeping it for enforcement scenarios (bailiffs, CCJs). Using it now wastes the one-time 60-day statutory shield on non-priority debt when no enforcement is imminent. Deploy only if a creditor escalates beyond collections letters.

**Iwoca collections trajectory (from advisor, 33 years experience):**
1. Miss 3+ payments → default letter (14 days to respond)
2. Account closed → sold to collection agency
3. Collection agency has no enforcement rights — letters only
4. If no arrangement: pre-action protocol → CCJ (6 years on register)
5. **This takes months.** Not weeks.

**Advisor's recommendation for Iwoca:** Offer £1/month + forward the StepChange budget. Shows good faith. If they don't accept, process runs its course through collections.

**Benefits status (mentioned in call):** ~£400 UC coming in(?). Advisor estimated total at ~£1,100 but rent/council tax reductions unclear (living with parents). **Status and exact figures need confirmation — update this section when known.**

**Next step:** Call Business Debtline (0800 197 6026) for Iwoca and Capital On Tap advice.

---

## Canonical B: Bankruptcy Architecture (2026-04-10)

**Status: UNDER CONSIDERATION — nothing decided. Requires IP consultation before action.**

### Thesis

File bankruptcy before June (dodge Iwoca step-up). Eliminate ~32k debt. Survive 12-month bankruptcy period at or below assessed needs threshold. Discharge clean. No IPA.

Credit rating sacrifice is assessed as irrelevant to stated trajectory (digital nomad, no mortgage, agency via business account).

### Needs threshold engineering

The OR assesses income against "reasonable domestic needs" using Common Financial Statement guidelines. If no surplus exists, no IPA is imposed. The strategy depends on legitimately raising assessed needs to a liveable figure:

| Expense | Monthly | Basis |
|---------|---------|-------|
| Living (food, meds, bills, subs) | ~994 | Current canonical burn minus debt service |
| Rent to parents | ~400-500 | Parents have genuine financial needs; adult child paying rent is recognised expense |
| Car (lease, insurance, fuel) | ~300-500 | Rural area, no public transport, needed for work and social independence |
| **Assessed needs (target)** | **~1,700-2,000** | |

At ~2,000/mo needs, earnings up to ~28-30k salary produce zero surplus. No surplus = no IPA.

### Earning during bankruptcy

- Employment and self-employment are both permitted during bankruptcy.
- Cannot be a company director — sole trader only (no Ltd).
- Self-employment: legitimate business expenses (compute, software, hosting) reduce assessable income before surplus calculation.
- Contractor model: company pays e.g. 2,500/mo, minus 500/mo business costs = 2,000/mo personal income = at threshold.
- Companies do not credit-check contractors. The bankruptcy is operationally invisible to clients.
- "Senior full-stack at sub-market rate" is an absurd bargain for the buyer. The pitch works.

### Family rent — risk factors

- OR scrutinises payments to "connected persons" (family).
- Rent must be genuine, at or below market rate, and not a mechanism to absorb surplus.
- Parents' own financial need is documentable and strengthens the case.
- This is the highest-risk element of the architecture. IP must confirm.

### Agency pilots during bankruptcy window

- Aura + Zodiac.fm pilots: ~500/mo combined revenue, ~24/mo compute cost.
- Sub-threshold income. Portfolio-building, not cash-flow play.
- Sole trader permitted. Business expenses further reduce assessable income.
- Post-discharge (month 13+): pivot to full-rate clients (1k setup + 1k/mo retainer). No OR involvement.

### Sequence (proposed, pending IP validation)

1. IP consultation — confirm needs assessment, IPA trigger point, family rent treatment, self-employment rules. **No timeline pressure. Parked until creditor responses, father discussions, and job market signal resolve. Will be scheduled when the picture is clearer.**
2. If architecture holds: file bankruptcy before June (avoid Iwoca 622/mo step-up)
3. 12-month window: agency pilots + sub-threshold contracting + portfolio building
4. Month 13: discharge. Earn freely. Scale agency. Take full-rate roles.

### vs Canonical A (Payment Suspension)

| Factor | Suspension | Bankruptcy |
|--------|-----------|-----------|
| Debt eliminated | No — deferred | Yes — written off |
| Interest | May continue accruing | Eliminated |
| OR involvement | None | Yes — 12-month oversight |
| Earning restriction | None | Must stay below needs threshold |
| Cost | 0 | 680 |
| Credit impact | Defaults (6 years) | Bankruptcy (6 years) |
| Iwoca June step-up | Still due unless creditor agrees | Never paid |
| Risk | Creditors may refuse suspension | OR may impose IPA if income exceeds needs |

### Open questions for IP

1. Realistic needs assessment for: rural, living with parents, car needed for work — what figure will the OR accept?
2. At what income does IPA typically trigger given those needs?
3. Family rent: what amount is defensible without challenge?
4. Self-employment: how are business expenses treated in surplus calculation?
5. Timing: any advantage to filing before vs after payment suspension emails are sent?
6. DRO (90 fee, same write-off): does it carry the same IPA exposure? StepChange couldn't answer this.
