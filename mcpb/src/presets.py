"""Analysis presets for different scenarios."""

ANALYSIS_PRESETS = {
    "security": {
        "prompt": """Security analysis - Look for potential threats:

ASSESS FOR:
- Unknown people (not family members)
- Suspicious or unusual activity
- Packages or deliveries
- Unusual objects or vehicles
- Animals (pets vs wildlife)
- Entry/exit activity

RESPOND WITH:
- Threat level: none/low/medium/high
- Description of what you see
- Specific security concerns
- Recommended action""",
        "description": "Security threat detection and assessment",
    },
    "food": {
        "prompt": """Food quality analysis:

ANALYZE:
- Food presentation and appearance
- Cooking status and doneness
- Color, texture, and quality indicators
- Plating and presentation
- Any quality concerns

PERFECT FOR:
- Monitoring schnitzel perfection!
- Cooking progress assessment
- Food safety evaluation""",
        "description": "Food quality and cooking analysis",
    },
    "pets": {
        "prompt": """Pet activity monitoring:

OBSERVE:
- Animals present and their species
- Pet behavior and activity
- Mood and demeanor indicators
- Interactions with environment
- Any concerning behaviors
- Play, rest, or feeding activities

GREAT FOR:
- Benny monitoring and activity tracking
- Pet behavior assessment""",
        "description": "Pet behavior and activity analysis",
    },
    "delivery": {
        "prompt": """Delivery detection:

CHECK FOR:
- Packages at door or entrance
- Delivery personnel present
- Delivery vehicles (trucks, vans, cars)
- Items left at entrance
- Delivery notifications needed

USEFUL FOR:
- Package delivery monitoring
- Entrance activity tracking""",
        "description": "Package and delivery monitoring",
    },
    "general": {
        "prompt": """General image analysis:

DESCRIBE:
- Main subjects and objects
- Activity or action taking place
- Notable details or anomalies
- Overall scene context
- Any items of interest

USEFUL FOR:
- General monitoring
- Activity logging
- Situational awareness""",
        "description": "General purpose image analysis",
    },
}
