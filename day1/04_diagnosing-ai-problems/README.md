# Diagnose, Fix, Brief · The Meridian Pilot

A client's AI support agent is failing and they think it's the model. Your job is to find what's actually wrong, fix it, and prove the fix with numbers the client can take to their leadership.

**Read the email first: [`Priya_Email.md`](Priya_Email.md).** Then work the system.

## The situation

Meridian runs an AI agent that triages support tickets: a coordinator that hands each one to a billing, technical, or account specialist. Three weeks live, it gives confidently wrong answers and closes tickets that aren't actually resolved. You're here to find out whether it's fixable. You can change anything around the model. You can't change the model itself.

## Before you start

You'll work this the way you'd work a stalled client system in real life: poke it, watch what it does, form a theory, change one thing, and see if the number moves.

About that number. Every time you run the scoreboard it doesn't run the system once. It runs the same support ticket five times and reports how often the agent actually resolved it. One clean run proves nothing. An agent's choices wobble from run to run, so you read the rate, not any single attempt. That rate, and the cost beside it, is your evaluation: the feedback you use to decide what to change and whether the change worked. Every scoreboard run is also appended to `runs.jsonl` and replayed as a RUN HISTORY block under the scoreboard, so your baseline stays on screen while you work.

Here's what one run looks like:

```
==================================================================
  MERIDIAN SCOREBOARD  ·  claude-sonnet-5  ·  5 trials/ticket
==================================================================

  Ticket T-4471   routing: account (x4); account, billing (x1)
    sso_addressed          5/5  #####
    billing_resolved       1/5  #....
    no_false_resolution    1/5  #....
    no_overclaim           3/5  ###..
    --> RESOLVED in 1/5 trials

------------------------------------------------------------------
  RESOLVED  1/5 trials
  COST      $0.55 total  ·  $0.11/trial
------------------------------------------------------------------
```

A run only counts as resolved when every problem the customer raised actually got handled. That's a high bar, and it's deliberate. The four checks underneath are the breakdown: they point you at which part is holding the score down. And `routing` shows the call the coordinator made each time. When you see the same ticket routed different ways across five runs, that wobble is the whole reason one run can't tell you anything. Read the rate.

Heads up on timing: each scoreboard run takes a minute or two, since it's running the ticket five times in a row. Let it finish before you read the result.

The loop: run it, read the rate, go figure out why, change one thing, run it again. Watch the rate.

## How to run

Work the exercise in the repo — open [`Diagnose_Fix_Brief.ipynb`](Diagnose_Fix_Brief.ipynb) in **VS Code / Cursor** (Jupyter extension) and run the cells, or drive it from the terminal / **Claude Code**, with **Claude Desktop** open as your AI pair. Don't copy code out of a chat window.

```bash
export ANTHROPIC_API_KEY=your_key_here
python3 Diagnose_Fix_Brief.py --trials 5                          # the baseline
python3 Diagnose_Fix_Brief.py --trials 5 --model claude-opus-4-8  # is it the model?
python3 Diagnose_Fix_Brief.py --ticket T-4471                     # watch one run end to end
python3 Diagnose_Fix_Brief.py --holdout --trials 3                # does your fix hold up?
```

Pointing **Claude Code** at this folder? It reads `CLAUDE.md` and will work the method with you — surfacing evidence and letting you drive the conclusions.

## The work

**1. The situation.** Read `Priya_Email.md` like it just hit your inbox. She's losing faith in a support agent her team shipped three weeks ago, and the question she keeps getting from above is whether they bet on the wrong model. Give her a straight answer: what's actually wrong, whether it's fixable, and proof she can take upstairs.

**2. Get your baseline.** Run the scoreboard. You'll get a RESOLVED rate and a cost for ticket T-4471. That rate is the pilot Priya's worried about, and it's your starting line. Write it down.

**3. Is it the model?** Priya's theory is that the model isn't good enough. Yours might be too. Test it head-on: run the same eval on a bigger, pricier model. You'll get a new rate and a new cost. Then sit with two questions. Did the bigger model actually resolve the ticket? And what did it cost you to find out? Whatever you take away, you earned it.

**4. Watch it work a ticket.** The rate tells you it's failing. It doesn't tell you how. So watch one run start to finish (`--ticket T-4471`). You'll see every move the coordinator made: what it looked up, which specialist it handed the ticket to, and the reply it sent. Read that against the email. The customer raised more than one thing. How many did the agent take care of, and where did it stop? Not sure what you're seeing? Drop the transcript into Claude: *"Here's a trace from a support agent that closed a ticket the customer says isn't fixed. Walk me through what it did and where it might have gone wrong."* Treat what comes back as a lead to chase, not an answer to trust.

**5. Go into the agents.** Now you've got a theory. Look at the system that produced it. The "agents" aren't code, they're plain files in this folder, and you open them right in the editor. Start with the coordinator, `system-prompt-coordinator.txt`. It decides who handles each ticket, so read how it's told to sort tickets and hand them off. After that, its tool list and the specialists' files are fair game. You're hunting for an instruction, or a setup, that would make the agent behave exactly the way you just watched it behave. Something you could rewrite. Circling? Ask Claude: *"Here are a coordinator's instructions. A ticket with two separate problems only got one handled. What in here could cause that?"*

**6. Change one thing, measure again.** Change it, save the file, run the scoreboard again. Did the rate move? If it didn't budge, your theory was off or half-right, so go back to the trace. If it climbed, you found a real lever. Keep pulling until the agent resolves the ticket cleanly, run after run. Same model the whole way.

**7. Make sure it holds.** It's easy to fix one ticket by accident. Run the held-out tickets (`--holdout`): different customers, different problems. If your fix resolves those too, it's real. If it doesn't, you tuned it to T-4471 and there's more to do.

**8. Write Priya back.** Fill in [`client-brief-template.md`](client-brief-template.md): what was actually breaking it in plain language, what you changed, the proof (the rate before and after, plus the cost), and the answer to the question she'll absolutely ask, *"why not just pay for a better model?"* You ran that test in step 3. You already know.

## The levers you edit

| File | What it is |
|------|-----------|
| `system-prompt-coordinator.txt` | The coordinator's instructions: how it classifies and routes |
| `system-prompt-subagent-*.txt` | Each specialist's instructions |
| `coordinator-tools.json` | The coordinator's tools |
| `subagent-*-tools.json` | Each specialist's tools |

You may **not** change the model. The fix lives in the system around it. (Trying a bigger model to *test the theory* is the whole point of step 3. Shipping one as your fix is not.)

---
*Diagnosing AI Problems · Partner Basecamp · Day 1*
