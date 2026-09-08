# Final pass v2 — what this round changed, and what is still open

**2026-09-08.** Covers the four phases run against the review brief: the
guarded meet, batch consistency, LaTeX consistency, and this report.
Submission is **10 September 2026**, so what remains open is listed with a
judgement about whether it can be closed in time.

## What was added to the thesis

**A new arm, and a rule to go with it.** `guarded_meet` in `src/contract.py`:
where the meet of the negotiated envelope and the platform's mandate is empty
but the mandate is not, enforce the mandate. It is the greatest satisfiable
lower bound of the two that is still at or below the mandate. Stated as a
corollary in Chapter 3, measured in the new Section 5.10.2. No Magentic agent,
prompt or message schema was touched; the arm's launcher differs from
`arm_c_meet.py` in one line.

**The single-batch reproduction of Table 5.8.** Thirty runs, all five arms
together, reported in Section 5.9.

**Seven consistency fixes**, one of which was a wrong number.

## The four measured results, in order of how much they matter

**1. The composed contract is never violated where it governs.** Zero breaches
on every governed round of all twenty guarded-meet runs, at every offset —
0 of 12, 21, 10 and 13. Where arm C-meet governs *nothing* at f ≥ 1.02 (zero
interventions across fifteen runs), the guarded arm governs 44 rounds and
breaches none of them. Overspend £3.45 → £0.30, £13.41 → £8.20, £16.51 → £7.02;
closure held at 15. *(`2026-09-08-guarded-meet-results.md`)*

**2. The guarantee does not extend to the marketplace, and the reason is
structural.** The registered prediction that it would (G1) is scored as a
failure. The residual £7.02 is entirely on pairs that never froze an envelope:
most pairs settle in one or two rounds, and a negotiated contract does not exist
until both sides have named a price. That is limitation B6, and it is why arm B
reaches £0.00 where this arm cannot. **The cost of letting agents write their
own contract is the exchange in which they write it.**

**3. The five-arm comparison survives being run in one batch.** Every
categorical claim reproduces, and arms B and C-meet settled 3 of 3 pairs on
every seed at zero variance — the two arms the safety claim rests on are the
two that do not vary. *(`2026-09-08-batch-consistency.md`)*

**4. Two cardinal numbers in Chapter 5 were single seeds, and now say so.**
Arm C's £0.48 overspend on `bargain_3_9` is £0.01 in the second batch. Arm A's
£0.00 is £1.93. Both batches settle twelve arm A deals with exactly one
breaching; they differ only in which row it breaches. Sections 5.1 and 5.9 now
state the disclosed-scenario result as the comparison against £21.70
undisclosed rather than as a zero.

## Errors found and fixed this round

**The guarded meet ran as arm B for six runs.** Four gates in `protocol.py`
named the inference arms by hand and none knew about the new theta source, so
the arm skipped the pre-phase, the freeze and the composition entirely. It
produced entirely plausible numbers while doing so. The only symptom was a
counter reading zero where it should have read 24. Fixed with one named
constant and a test pinning it against the declared type; the six runs were
dropped. **This is the most instructive failure of the round: a passing test
suite, a clean exit and believable numbers, all while measuring the wrong arm.**

**"37 of 37" should have been "64 of 64".** Section 5.10 disagreed with its own
table three paragraphs above it. Replay against the database gives 64; the
£16.51 alongside it is correct.

**Limitation B4 conflated two different empty safe sets.** An empty *mandate*,
where nothing can comply and declining to filter is right; and an empty
*composition* over a satisfiable mandate, where the platform declines to enforce
a requirement it holds. Only the first raises the ethical question Section 7.4.2
asks, and only the second is a defect. Split in the appendix and in 7.4.2.

**`arm_a_no_contract.py` silently reports the wrong scenario without `--live`.**
It defaults to replaying the recorded `mexican_3_9` baselines. Caught by the
replay returning zero proposals for the batch schemas. Documented in the
batch-consistency note; the script's own docstring already said so.

## Still open, with a judgement on each

**The presentation does not exist.** It is 15% of the mark. This is the largest
outstanding item by expected value and nothing in this round touched it.
*Closeable before the 10th, and should be the next thing done.*

**The body is 70 pages against a 40–60 norm**, and this round added roughly two
pages. *Not closeable by careful trimming in the time left; a deliberate cut
would be needed and that is a supervisor conversation.*

**Neither supervisor is cited.** *Trivially closeable, and worth doing.*

**Both pasted API keys should be rotated** — the Anthropic and Groq keys both
appear in a transcript. *Do after submission, not before; rotating now risks
breaking a run.*

**`results/summary/five_arms.json` is stale.** It predates the 2026-08-12
re-verification and still carries the retracted 0.111 correction rate.
`science_data.py` documents this and no figure reads it. *Leave; deleting it
would break the audit trail that records why it is wrong.*

**Coupling has run live and never activated** (limitation C4), and **the
convergence theorem is untested on live agents**. Both are stated plainly in
Chapter 8 as things not established. *Not closeable; correctly scoped as
limitations rather than claims.*

**`run_open_weight_sweep.sh` is broken as shipped** — `llama-3.3-70b-versatile`
is retired and returns 404. *Either fix the model name or delete the script; it
is referenced nowhere the thesis depends on.*

## Spend

Roughly £5 this round: 20 guarded-meet runs, 6 discarded, 30 batch runs. The
cumulative figure since 2026-09-07 cannot be verified from the artifacts —
there is no token accounting in the run records — and only the Google AI Studio
billing page has the real number. The run count since then is 176.
