"""
Intent patterns for the rule-based AI assistant.
Each intent maps natural-language trigger keywords to a controlled,
parameterized database operation defined in ai_services.py.
No raw user-supplied SQL is ever executed — this file only maps *intent*,
never query text.
"""

INTENT_EXAMPLES = [
    "How many laptops are available?",
    "Which assets are assigned to the IT department?",
    "Who has asset LAP-1024?",
    "What maintenance is currently pending?",
    "Which software licenses expire next month?",
    "Show assets assigned to employees in HR.",
    "Which assets have high maintenance costs?",
    "Which assets have repeated maintenance issues?",
    "Which licenses need renewal?",
    "Which department has the highest asset cost?",
    "How many pending requests are there?",
    "Show unassigned assets.",
]
