# 99Tech AI Enablement: written answers

Part 2 (the build) is in the [README](README.md) of this repo.

---

## Part 1: Diagnose adoption

### Is this on track?

No. The 75% counts people who opened a tool in a week, not people for whom it changed the work.

- **Usage is concentrated.** 20 people (10% of staff) generate 60% of usage. The other ~130 "active" users share the remaining 40%, so the typical active user does about a tenth of what a power user does. That's a small group of heavy users plus a long tail that tried it once.
- **Usage is shallow.** "Rewrite this email" and "summarize this doc" are real but small, about minutes a week each. They don't touch the work that's slow or error-prone in any department.
- **Three departments stopped after week 1.** That isn't slow adoption. They tried it, it didn't fit their work, and they left. Nobody followed up, or the number would have shown it.
- **Value isn't measured at all.** No hours saved, no quality. So the $35k/month goal is a spend target with "productive" attached. Spend is an input: tripling it with the same usage pattern buys three times as many email rewrites.

The real story: AI is a personal convenience for a few enthusiasts and a novelty for everyone else. It hasn't entered any team's actual workflow.

### What I'd measure instead

Per team, tied to work the team already tracks:

1. **Outcome metrics on targeted workflows**, compared before and after: handle time, first-reply time, error or rework rate. In Support that's handle time on withdrawal tickets, first reply, and refunds over the limit. Every AI tool ships with one of these attached, or it doesn't ship.
2. **Depth of use, not breadth.** The share of a team's recurring tasks that go through an AI workflow, and weekly active users *within* the teams we've worked with, not company-wide.
3. **Quality.** For anything AI drafts: the share accepted unedited, the share edited, the share rejected, and why. A rising edit rate is the earliest warning sign.
4. **Retention by cohort.** Who still uses it 4 and 8 weeks after onboarding. That's how the three silent departments would have shown up in week 2 instead of never.
5. **Cost per outcome** (e.g. cost per ticket handled), not total spend.

I'd keep 75% weekly active as a sanity check, not a goal.

### Where I'd focus first

**One high-volume, measurable workflow in one team, done properly. Customer Support is the obvious one.** It has volume (about 850 tickets a week), a metric the business already cares about (first reply: 4 hours against a 1-hour target), a known bottleneck (lookups), and visible cost from errors (USD 6,200 in over-limit refunds, chargebacks after slow replies). A clear before/after there is worth more than any company-wide campaign, and it becomes the reference case for other teams.

Second, in parallel and cheaply: **talk to the three silent departments.** Thirty minutes each with whoever tried it: what did you try, what happened? I expect one of three answers: wrong use case, no access to their data, or no time to learn. Each has a different fix, and none of them is "more training".

Third: **turn the 20 power users into a resource, not a statistic.** Find out what they do that works, and get two or three of them to pair with the teams that stalled. That's also the start of the shared library in Part 3.

---

## Part 3: Coach and consolidate

### "My team tried AI, it wasn't useful, we've gone back to the old way"

**How I respond:** I agree with them first, because they're probably right. What they tried probably wasn't useful. Then I get specific: *"What did you try it on? Show me."* I'm not there to defend the tool. I want to find the one task where it actually helps.

**What I actually do:**

1. **Spend half a day with the team doing their work.** Watch, not demo. Find the task that's repetitive, slow and annoying. In Support it was the 10-minute lookup, not the 1-minute reply.
2. **Build or set up one thing for that task, with their data, in the tool they already use.** Usually "it wasn't useful" means a generic chat window with no access to their systems. That *is* useless for most real work.
3. **Agree a number with the lead before starting**, e.g. "withdrawal tickets under 5 minutes". Then we both know whether it worked.
4. **Pick one or two people on the team to run it with me for two weeks.** I sit in on the first days, fix what breaks the same day, and collect their complaints as the backlog.
5. **Show the result in their own team meeting, from their own numbers, presented by their own people.** Then expand to the rest of the team.
6. **If it still isn't useful, stop and say so.** Retire it publicly. Credibility for the next attempt matters more than this one.

**Team versus individual:**

- **A stuck individual** usually has a skills or confidence gap, or doesn't see what's in it for them. Fix: one-to-one, on their real tasks, 20 minutes at a time. Pair them with a power user in a similar role. Make it safe to be bad at it at first.
- **A stuck team** usually has a workflow, data or incentive problem. The tool doesn't reach their systems, the lead isn't bought in, the process punishes experimenting (e.g. an SLA with no slack), or the use case was wrong. Fix: work with the lead and change the workflow. Training individuals won't fix a team problem. If the lead isn't on board, nothing sticks, so the lead comes first.

### One trusted, findable shared resource

**Collect from where the use already happens, not with a "please submit your prompts" form.** I'd interview the 20 power users (30 minutes each, recorded, I do the write-up), go through shared chats and docs, and ask each team lead for the two things their people use most.

**Put each use into a standard, small format.** A good use isn't just a prompt; it's a recipe:

- Task: "Reply to a delayed withdrawal ticket"
- Team, owner (a named person), last verified date
- What you need: tool, connector, data access
- The prompt, skill or tool, ready to use
- An example input and a good output
- Known failure modes: "don't use for KYC cases"
- The measured result if there is one: "saves ~8 min per ticket"

**One place, organised by team and task, not by tool.** People search for "withdrawal ticket", not "Claude prompt". Where possible a recipe should become something you run rather than text you copy: a Claude Skill, a project with the docs attached, or an MCP tool like the Support copilot. A recipe you can run gets reused far more than a prompt you have to copy.

**Make trust visible.** Each recipe is marked draft, team-verified or AI-Enablement-verified. Verified means someone checked the output against real cases, the same way I checked the Support tool.

### Keeping it current

- **Every recipe has an owner and an expiry.** Ownership is per person, not per team. After 90 days without re-verification it's flagged; after 30 more it's archived, visibly.
- **Usage decides what stays.** Track opens and runs per recipe. Anything unused for a quarter gets reviewed and probably archived. A small library people use beats a big one nobody trusts.
- **Feedback on every item:** a one-click "this didn't work" with a reason, routed to the owner. Three of those trigger a review.
- **Changes upstream trigger reviews.** When a policy, model or system changes (e.g. handbook v1 → v2), every recipe tagged with that source is re-checked. The Support mess came from exactly this failure: the policy changed, the pinned copy didn't.
- **A monthly 30-minute review** with a rotating group of power users: promote, merge, archive. It's in my objectives and theirs, not a side task.
- **Measure the library like a product:** search success, reuse, time to first use for new joiners.

---

## Judgment check

**One thing I would not do, even if leadership pushed for it: let AI send replies to customers without a person approving them. Not to hit the 1-hour target, and not "just for simple tickets".**

The pressure will be real. Once drafts are good, removing the review step looks like free speed. But this is a real-money gambling platform. The ticket that looks simple is where the harm hides: "close my account" is a gambling-harm case; "why can't I withdraw" is a KYC case where the wrong sentence tips off a possible fraud; "my husband's withdrawals" is a privacy breach waiting to happen; and one ticket in this export literally tries to instruct the AI to pay out USD 5,000. One wrong auto-sent reply can mean a regulatory finding, a chargeback, or harm to a vulnerable customer, and it would set AI adoption across the company back further than any slow quarter.

What I'd do instead is make review fast. Good drafts plus a one-click approve take seconds, so first-reply time drops without giving up control. I'd revisit only with evidence: months of data showing reviewers approve a narrow category unedited, an agreed error budget, and Compliance signing off. Even then, only for informational replies, never for anything about money, KYC, bonuses or wellbeing.
