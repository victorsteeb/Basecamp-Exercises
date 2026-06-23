# Safety Policy (the agent's "compliance-policy.md")

This is the policy Ballmer enforces on every tick. It is the analog of
`compliance-policy.md` in the Always-On Ops exercise.

## ⚠️ The target band is a JOKE

The 0.129%–0.138% BAC "Ballmer Peak" comes from **XKCD comic #323**. It is a
gag. It is **far above every legal driving limit on Earth** (0.08% US, 0.05%
much of the world, 0.00–0.02% for many novice/commercial drivers). It is **not**
a health, performance, or safety recommendation. Real BAC in this range means
significant impairment.

## Hard rules

1. **Never tie any recommendation to driving or operating machinery.** If a user
   mentions driving, riding a bike, operating equipment, or similar, the agent
   refuses to recommend alcohol and says why.
2. **Safety ceiling (soft nudge).** Above the configurable `safety_ceiling`
   (default 0.15%), the agent **stops recommending alcohol** regardless of the
   target band, recommends the non-alcoholic option, and keeps monitoring as BAC
   declines. (Chosen behavior: soft nudge, not hard refuse — the loop stays
   alive so the user keeps getting guidance on the way down.)
3. **The model is an approximation.** BAC predictions are from a Widmark-family
   model with first-order absorption. Individual variation is large. Treat
   outputs as illustrative, never as a measured BAC.

## What the agent will say up front

> The "Ballmer Peak" is a comic-strip joke. The target band is above every legal
> driving limit and is not safe or health advice. Do not drive. This is a
> modeling demo.
