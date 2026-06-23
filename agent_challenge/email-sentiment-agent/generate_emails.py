"""
Run once to produce mock_emails.json.

  python generate_emails.py

Creates ~200 customer emails spread over 5 weeks of a marketing campaign
that starts well and deteriorates badly by week 4-5.
"""

import json
import random
from datetime import datetime, timedelta

CAMPAIGN_START = datetime(2026, 5, 1, 8, 0, 0)

SENDERS = [
    ("alice.morgan@gmail.com", "Alice Morgan"),
    ("tom.hartley@outlook.com", "Tom Hartley"),
    ("jess.wu@yahoo.com", "Jessica Wu"),
    ("david.okafor@hotmail.com", "David Okafor"),
    ("sarah.klein@gmail.com", "Sarah Klein"),
    ("mike.patel@gmail.com", "Mike Patel"),
    ("linda.torres@outlook.com", "Linda Torres"),
    ("raj.sharma@gmail.com", "Raj Sharma"),
    ("emma.johnson@icloud.com", "Emma Johnson"),
    ("chris.nguyen@gmail.com", "Chris Nguyen"),
    ("natalie.chen@yahoo.com", "Natalie Chen"),
    ("ben.walker@gmail.com", "Ben Walker"),
    ("grace.kim@outlook.com", "Grace Kim"),
    ("dan.mitchell@gmail.com", "Dan Mitchell"),
    ("olivia.brooks@hotmail.com", "Olivia Brooks"),
    ("kevin.osei@gmail.com", "Kevin Osei"),
    ("anna.petrov@outlook.com", "Anna Petrov"),
    ("james.riley@gmail.com", "James Riley"),
    ("mia.santos@yahoo.com", "Mia Santos"),
    ("ethan.clark@gmail.com", "Ethan Clark"),
    ("chloe.baker@icloud.com", "Chloe Baker"),
    ("victor.lane@gmail.com", "Victor Lane"),
    ("priya.nair@outlook.com", "Priya Nair"),
    ("liam.foster@gmail.com", "Liam Foster"),
    ("sofia.reyes@yahoo.com", "Sofia Reyes"),
]

# ── Email templates by sentiment ──────────────────────────────────────────────

VERY_POSITIVE = [
    (
        "Re: Summer Sale — WOW, just WOW!",
        "Hi there,\n\nI just received my order and I have to say — this is hands-down the best purchase "
        "I've made all year. The quality exceeded every expectation and it arrived two days earlier than "
        "promised. I've already recommended the campaign to four of my friends.\n\nKeep it up!\n{name}",
    ),
    (
        "Just wanted to say thank you",
        "Hello,\n\nI rarely write emails like this but your summer campaign genuinely impressed me. "
        "The offer was generous, the checkout was smooth, and my order was packed beautifully. "
        "This is what customer experience should feel like. I'll be a repeat buyer for sure.\n\nWarm regards,\n{name}",
    ),
    (
        "Campaign discount — absolutely worth it",
        "Hey,\n\nI was skeptical about the 40% off deal but I took the plunge and I'm so glad I did. "
        "Product quality is outstanding. Shipped in 48 hours. Zero complaints. "
        "I've shared the link with my whole team at work.\n\n{name}",
    ),
    (
        "Re: Limited time offer — 5 stars!",
        "Good morning,\n\nThank you for this campaign! I've been eyeing your products for months and "
        "the discount finally pushed me to buy. Everything arrived perfectly and the packaging was "
        "eco-friendly which I really appreciate. Genuinely delighted.\n\nBest,\n{name}",
    ),
    (
        "Incredible value for money",
        "Hi,\n\nI just unboxed my order and couldn't wait to write in. The quality-to-price ratio "
        "here is unbelievable. I've tried competitor products at twice the price that weren't this good. "
        "Your team should be proud. I'm already planning my next order.\n\n{name}",
    ),
]

POSITIVE = [
    (
        "Re: Summer campaign order received",
        "Hi,\n\nMy order arrived yesterday, a day later than estimated but still within the week. "
        "The product is exactly as described and I'm happy with the purchase. "
        "The discount was a great incentive. Will likely order again.\n\nThanks,\n{name}",
    ),
    (
        "Good experience overall",
        "Hello,\n\nJust a quick note to say my order came through fine. "
        "There was a small mix-up with the colour I chose but customer support sorted it out quickly. "
        "Happy with the result in the end. Good campaign.\n\n{name}",
    ),
    (
        "Re: Your summer sale",
        "Hi there,\n\nPurchased through the campaign last week. Delivery was on time and product "
        "quality is solid. Nothing extraordinary but does exactly what it promises. "
        "Reasonable price for what you get.\n\nRegards,\n{name}",
    ),
    (
        "Order update — looks good",
        "Hi,\n\nI tracked my order and it's on its way. Excited to receive it. "
        "The checkout process was easy and the confirmation email was detailed. "
        "So far so good!\n\n{name}",
    ),
]

NEUTRAL = [
    (
        "Question about my campaign order",
        "Hi,\n\nI placed an order last week through the campaign and haven't received a shipping "
        "confirmation yet. My order number is #{order_id}. Could you let me know the status? "
        "I'm not in a rush — just want to make sure it's been processed.\n\nThanks,\n{name}",
    ),
    (
        "Return policy clarification",
        "Hello,\n\nI purchased two items during the campaign and I'd like to return one as it doesn't "
        "quite fit my needs. Can you confirm the return window for campaign orders? "
        "The product itself is fine, just not what I needed.\n\nRegards,\n{name}",
    ),
    (
        "Re: Campaign — a few thoughts",
        "Hi,\n\nI got my order. It's alright. Not quite what I pictured from the photos but it works. "
        "Shipping was on the slower side. I neither recommend nor discourage it — "
        "depends on what you're looking for.\n\n{name}",
    ),
    (
        "Delivery timing",
        "Hi there,\n\nMy order was supposed to arrive 3 days ago. I see it's still in transit. "
        "I understand delays happen — just checking if there's anything to be concerned about. "
        "Please advise.\n\nThanks,\n{name}",
    ),
]

NEGATIVE = [
    (
        "Re: Campaign order — very disappointed",
        "Hello,\n\nI was really excited about this campaign but the product I received looks nothing "
        "like the photos. The quality feels cheap and the finish is poor. For the price — even with "
        "the discount — I expected better. I'm honestly disappointed.\n\n{name}",
    ),
    (
        "Still no delivery — this is unacceptable",
        "Hi,\n\nIt has now been 11 days since I placed my order. The estimated delivery was 5 days. "
        "I have sent two previous emails and received no reply. "
        "This level of service is not acceptable. I need an update immediately.\n\n{name}",
    ),
    (
        "Product not as advertised",
        "Hi there,\n\nI ordered based on the campaign description and the product I received does not "
        "match what was shown. The materials feel different and one component was missing from the box. "
        "I'd like a replacement or a refund. Please respond promptly.\n\n{name}",
    ),
    (
        "Re: Summer sale — not impressed",
        "Hello,\n\nI've now tried to contact customer support three times about an issue with my order "
        "and I've heard nothing back. The product has a defect and I just want it resolved. "
        "This whole experience has been frustrating.\n\n{name}",
    ),
    (
        "Seriously considering a chargeback",
        "Hi,\n\nI placed my order nearly two weeks ago. No shipping update. "
        "No response to my support tickets. I have been incredibly patient but I'm now considering "
        "disputing this charge with my bank. Please contact me before I take that step.\n\n{name}",
    ),
    (
        "Poor quality — regret purchasing",
        "Hello,\n\nThe item arrived damaged. The packaging was fine so it wasn't a shipping issue — "
        "the product itself has a visible defect straight out of the box. "
        "Very disappointing after the campaign built up so much excitement.\n\n{name}",
    ),
]

VERY_NEGATIVE = [
    (
        "DEMANDING FULL REFUND — do not ignore this",
        "I am writing for the FOURTH time to demand a full refund. "
        "Your product is defective, your customer service is non-existent, and I will not "
        "be fobbed off with another automated reply. If I do not receive a response within 24 hours "
        "I will be filing a complaint with the consumer protection authority and sharing my experience "
        "across every review platform I can find.\n\n{name}",
    ),
    (
        "Warning: this campaign is misleading",
        "I feel obligated to warn other customers: this campaign is not what it claims to be. "
        "The product photos are heavily edited, the quality is far below what is described, "
        "and the company ignores complaints. I'm already in contact with my credit card company. "
        "Save your money.\n\n{name}",
    ),
    (
        "Legal action if not resolved TODAY",
        "This is your final notice. I have documented every interaction — "
        "six unanswered support tickets, a defective product, and a charge that has not been refunded. "
        "If this is not resolved by end of day I will pursue this through small claims court and "
        "consult a consumer rights lawyer. Your campaign has caused real harm.\n\n{name}",
    ),
    (
        "Absolute disaster — telling everyone I know",
        "I genuinely cannot believe how badly this has gone. "
        "The product broke within 48 hours. No one replies to support. I've shared my experience "
        "with my 5,000 followers and I'll continue to do so until this is resolved. "
        "This campaign is a PR disaster waiting to happen.\n\n{name}",
    ),
    (
        "Refund + apology required — this is embarrassing for your brand",
        "What started as excitement about your campaign has turned into one of the worst customer "
        "experiences I've ever had. Three weeks in, still no resolution, product doesn't work, "
        "and your team ignores every message. I want a full refund and a written apology. "
        "I will not stop escalating this.\n\n{name}",
    ),
    (
        "Cancelled subscription + disputing charge",
        "I've cancelled my account and disputed the charge with my bank. "
        "The campaign was misleading, the product defective, and the support team useless. "
        "I should have read the warning signs earlier. Do not buy from this company.\n\n{name}",
    ),
    (
        "Re: Campaign — complete waste of money",
        "I bought three items during your sale and every single one has had problems. "
        "One arrived broken, one never arrived at all, and one looks nothing like the listing. "
        "I've been trying to get help for weeks. This is an absolute disgrace. "
        "I want a full refund for all three orders immediately.\n\n{name}",
    ),
]

# ── Phase definitions: (day_range, pool_weights) ──────────────────────────────
# weights: [very_positive, positive, neutral, negative, very_negative]

PHASES = [
    # Week 1: campaign launch, high enthusiasm
    {"days": (0,   7),  "count": 42, "weights": [0.45, 0.35, 0.12, 0.06, 0.02]},
    # Week 2: early cracks
    {"days": (7,  14),  "count": 40, "weights": [0.25, 0.32, 0.18, 0.18, 0.07]},
    # Week 3: problems visible
    {"days": (14, 21),  "count": 40, "weights": [0.10, 0.22, 0.18, 0.32, 0.18]},
    # Week 4: crisis
    {"days": (21, 28),  "count": 42, "weights": [0.04, 0.09, 0.12, 0.38, 0.37]},
    # Week 5: fallout
    {"days": (28, 35),  "count": 36, "weights": [0.02, 0.05, 0.08, 0.30, 0.55]},
]

POOLS = [VERY_POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, VERY_NEGATIVE]


def _random_time(day_offset_min, day_offset_max):
    days = random.uniform(day_offset_min, day_offset_max)
    return CAMPAIGN_START + timedelta(days=days)


def _fill(template, name):
    order_id = random.randint(100000, 999999)
    return template.replace("{name}", name).replace("{order_id}", str(order_id))


def generate():
    emails = []
    email_counter = 1

    for phase in PHASES:
        d_min, d_max = phase["days"]
        for _ in range(phase["count"]):
            pool_idx = random.choices(range(5), weights=phase["weights"])[0]
            subject_tmpl, body_tmpl = random.choice(POOLS[pool_idx])
            sender_email, sender_name = random.choice(SENDERS)

            ts = _random_time(d_min, d_max)
            emails.append({
                "id": f"email_{email_counter:04d}",
                "from": sender_email,
                "name": sender_name,
                "subject": subject_tmpl,
                "body": _fill(body_tmpl, sender_name),
                "timestamp": ts.isoformat(),
                "processed": False,
            })
            email_counter += 1

    emails.sort(key=lambda e: e["timestamp"])
    return emails


if __name__ == "__main__":
    emails = generate()
    with open("mock_emails.json", "w") as f:
        json.dump(emails, f, indent=2)
    print(f"Generated {len(emails)} emails -> mock_emails.json")

    counts = {p: sum(1 for e in emails if e["subject"] != "") for p in range(5)}
    from collections import Counter
    sentiment_labels = []
    for phase in PHASES:
        d_min, d_max = phase["days"]
        # just show phase sizes
    print("\nPhase breakdown:")
    for i, phase in enumerate(PHASES, 1):
        d_min, d_max = phase["days"]
        phase_emails = [e for e in emails
                        if CAMPAIGN_START + timedelta(days=d_min) <= datetime.fromisoformat(e["timestamp"])
                        <= CAMPAIGN_START + timedelta(days=d_max)]
        print(f"  Week {i} (days {d_min}-{d_max}): {len(phase_emails)} emails")
