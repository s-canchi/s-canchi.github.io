---
layout: post
title: How to Build Confidence in Your Code
subtitle: Test rigor, real bugs, and judgment calls
tags: [testing, debugging, software engineering, research software]
comments: true
---

I recently ended up designing a more detailed test plan alongside a new feature, not as the main task but as a side quest. The scope started narrow, just the feature branch, with the idea that it could generalize later. Testing on this project has mostly meant running the whole pipeline and comparing the output against reference results. My instinct, coming off years on the data-analysis side of things where correctness and reproducibility are the whole job, was to be thorough from the very first commit: small simulated datasets, checked at nearly every commit, for completeness.

Looking back, that was probably more than the feature needed this early on. There was no existing test convention on this codebase to follow, so being careful felt like the safer choice. But an early prototype and a stable, mature feature don't need the same amount of proof. I was treating them the same. The real question isn't whether I was too careful. It's how you match testing effort to where a piece of work actually is, since that answer changes as the work moves along.

## How much testing depends on where you are

The clearest way I have found to think about this is four separate questions, not one:

| Axis | Question it answers | Example values |
|---|---|---|
| **Type** | What is actually being checked? | Is it right? Did it change? Is it repeatable? Is bad input rejected? |
| **Scope** | How much of the system runs in one check? | One function alone, a few functions wired together, the whole system end to end |
| **Scale** | How big or realistic is the input? | A tiny hand-built case, a realistic medium case, full real-dataset size |
| **Cadence** | How often does a given check need to run? | Every commit, before merging something substantial, only at a milestone |

These four get lumped together under one word, testing, but they answer different questions. Scope and scale can move independently, even though they feel like the same thing. Each one needs a different answer depending on where a project stands, not one fixed setting you pick and keep.

Here's roughly how I actually leaned on each axis as this feature moved along, and it doesn't match a clean "ramp up over time" story. Type mattered a lot from day one, just not the way I expected going in. Most of the early work changed code paths that already existed. Checking for regression against that existing behavior was critical from the very first commit, not something to defer. Fail-fast checks, whether bad input gets rejected loudly, mattered the same amount no matter the phase; that one never really loosens. Scope was wider early on too. Checking for divergence from existing paths meant exercising those paths end to end, not narrow checks on isolated pieces.

Cadence was the axis that did tighten as things settled. Functions with one clear right answer got a fast check on every commit, even ones that looked unrelated to that day's change. The point of that layer was a cheap floor, not a targeted check. Parts still being redesigned stayed loose. A precise test there would just get rewritten the next time the design moved, so a loose invariant, or nothing yet, made more sense.

Scale was the last thing to widen, and that's where two different kinds of surprises showed up. One looked like a scale problem but wasn't: a standalone version of one code path had quietly drifted out of step with its integrated twin, and nothing caught it until I ran the whole pipeline end to end at real size. The actual lesson there was about code drift between duplicate logic, not about scale itself, scale was just where it happened to surface first. The other kind is a real property of the data: some rare cases are genuinely invisible in anything smaller, no matter how deliberately you try to build a test for them.

## A few lessons that go beyond this one project

A few of the bugs from this process weren't really about this codebase. They're more general lessons about testing and debugging.

**The bug that wasn't a bug in the code.**
- **What happened:** I optimized a step, validated it on a subset, then ran it at full scale. A cost model from input size and per-step timing can tell you if the input explains a slowdown, not if the machine does. A couple of runs didn't match the model, and it turned out to be the hardware the job landed on, not the code.
- **What was missing:** any way to measure normal machine-to-machine variation.
- **Fix:** a small, cheap benchmark on the hardware itself, run alongside every job rather than once, since shared clusters vary run to run.

**The threshold search that quietly picked the wrong answer.**
- **What happened:** A routine was meant to derive a cutoff per bin, scanning candidates and returning the loosest one that passed. It returned the first, tightest one instead, so every derived cutoff quietly landed on the same edge of the grid. Each result looked reasonable alone; it was only caught because several supposedly independent derivations came out identical.
- **What was missing:** any check that independent derivations shouldn't agree exactly.
- **Fix:** a one-line correction to which candidate the scan returns, plus checking new derivations against each other going forward.

**The bugs that a green check never touched.**
- **What happened:** Before merging a substantial change, I read through the new logic line by line instead of running it. That pass alone turned up six real defects. The regression check for this feature had stayed green the whole time, and checking its own test data afterward confirmed it held zero cases that could trigger any of the six.
- **What was missing:** test data that actually exercised those six code paths, and any way to know that check had a hole that large while it kept passing.
- **Fix:** the six defects themselves, plus checking test data against a change's actual logic before trusting a green run, not only after something goes wrong.

## Bad data is a separate problem from bad code

This sits outside the four axes above entirely. It splits into two different questions: is the input trustworthy before your code runs, and does data quietly go bad after your own code has already touched it.

| Where | What goes wrong | How it's caught |
|---|---|---|
| Input, structural | Missing, malformed, or empty data | Caught in advance: a check knows exactly what wrong looks like ahead of time |
| Input, semantic | Well-formed but simply wrong: mislabeled, shifted, corrupted somewhere upstream, still looks plausible | Not catchable in advance, the same no-ground-truth problem, just applied to the input instead of the output |
| Inside your own code | A stage's own output silently goes stale or incomplete: a merge skips part of what it should combine, a cached result outlives the run that produced it | Not an input-trust problem, the data was fine to start; only surfaces once a later stage depends on the drifted result |

## A few calls I made without a clear right answer

None of these had an obvious right answer at the time, and I'm still not sure I'd defend all of them the same way in hindsight.

- I gated the biggest, most realistic checks to run by hand at milestones only, unsure that scales well long term.
- Deciding which logic gets an exact expected value versus only a bounds check was a judgment call each time, not a fixed rule.
- I still haven't automated the cheapest, fastest checks, partly worried a partial setup creates more false confidence than none at all.
- I picked "before merging something substantial" as the trigger for the next tier up mostly because it was easy to justify in the moment.

I don't think there's one right amount of testing, only the right amount for where a project stands right now. That's still the part I'm working out, on this project and probably every one after it.
