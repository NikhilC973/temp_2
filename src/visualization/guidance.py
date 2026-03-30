"""
Program Guidance — Actionable recommendations based on emotional trajectories.

Updated: Extended to 7 phases with verified-event-informed timing guidance.
"""

TIMING_GUIDANCE = [
    {
        "phase": "Event Window (0–24h)",
        "dominant_emotions": "Fear, Anger, Surprise",
        "recommended_actions": "Crisis communications, safety alerts, know-your-rights dissemination",
        "channels": "Text alerts, community WhatsApp, neighborhood radio",
        "priority": "CRITICAL",
    },
    {
        "phase": "Post-Raid Week 1 (Days 2–7)",
        "dominant_emotions": "Anger, Fear → Gratitude emerging",
        "recommended_actions": "Legal aid hotlines, trauma-informed counseling, mutual aid fund activation, property damage documentation",
        "channels": "Community meetings, legal clinics, social media",
        "priority": "HIGH",
    },
    {
        "phase": "Post-Raid Week 2 (Days 8–14)",
        "dominant_emotions": "Gratitude, Pride emerging, Anger sustained",
        "recommended_actions": "Mutual aid scaling, school support protocols, tenant organizing, media advocacy",
        "channels": "Neighborhood organizations, churches, schools, news outlets",
        "priority": "HIGH",
    },
    {
        "phase": "Extended Monitoring (Weeks 3–5)",
        "dominant_emotions": "Gratitude, Pride dominant, Fear declining",
        "recommended_actions": "Policy advocacy, long-term mental health services, community documentation, legal case support",
        "channels": "City council, NIJC, policy organizations, investigative journalism partnerships",
        "priority": "MEDIUM",
    },
    {
        "phase": "Court Action & Tenants Union (Weeks 6–8)",
        "dominant_emotions": "Anger resurgence, Sadness, Gratitude",
        "recommended_actions": "Tenant union support, housing advocacy, court monitoring, relocation resource coordination",
        "channels": "Legal aid orgs, housing authorities, CHA, aldermanic offices",
        "priority": "HIGH",
    },
    {
        "phase": "Forced Displacement (Weeks 9–10)",
        "dominant_emotions": "Sadness, Anger, Fear resurgence",
        "recommended_actions": "Emergency relocation assistance, housing navigation, continued mental health support, homelessness prevention",
        "channels": "Homeless prevention hotlines, mutual aid networks, Section 8 coordination, warming centers",
        "priority": "CRITICAL",
    },
]

KEY_FINDINGS = {
    "critical_window": "5–7 days post-event: Community emotion shifts from crisis fear to organized action. This is the maximum-impact window for service providers.",
    "second_crisis": "Weeks 6–10: Court-ordered displacement creates a second emotional crisis peak — anger and sadness resurge as families face eviction deadlines.",
    "fear_trajectory": "Fear peaks at t=0, declines steadily through Week 3, but shows secondary spike during displacement phase as housing insecurity triggers re-traumatization.",
    "gratitude_pattern": "Gratitude emerges Day 3–5 as mutual aid activates, peaks Weeks 3–5 during community organizing, then dips during displacement.",
    "resilience_evidence": "Pride/joy metrics increase monotonically from Week 2 through Week 5, indicating genuine community resilience formation — before being disrupted by forced displacement.",
    "platform_differences": "Reddit discourse skews toward anger/advocacy; news comments skew toward sadness/empathy; YouTube comments show higher emotional intensity overall. Channel strategy should account for this divergence.",
}
