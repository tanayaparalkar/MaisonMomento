import re

with open("static/css/storefront.css", "r") as f:
    css = f.read()

# 1. Scent-finder-widget background
css = css.replace(
    "background: linear-gradient(165deg, #fdfbf7 0%, #f6f0e6 100%);\n    border: 1px solid #dcd2bf;",
    "background: #fffbf2;\n    border: 1px solid #e8e3d8;"
)

# 2. Scent-finder-widget golden bar
css = css.replace(
    "background: linear-gradient(90deg, #b89047 0%, #e2cf98 50%, #b89047 100%);",
    "display: none;"
)

# 3. scent-purpose-tab is-active
css = css.replace(
    "background: #ffffff;\n    color: #1a1613;",
    "background: var(--deep-navy, #1a2936);\n    color: var(--ivory, #f4f4f2);"
)

# 4. scent-quiz-submit-btn
css = css.replace(
    "background: linear-gradient(135deg, #9c7336 0%, #b89047 50%, #896229 100%);\n    color: #ffffff;\n    border: 1px solid #cbb382;",
    "background: var(--deep-navy, #1a2936);\n    color: var(--ivory, #f4f4f2);\n    border: 1px solid var(--deep-navy, #1a2936);"
)
css = css.replace(
    "box-shadow: 0 4px 14px rgba(156, 115, 54, 0.35);",
    "box-shadow: 0 4px 14px rgba(26, 41, 54, 0.25);"
)
css = css.replace(
    "box-shadow: 0 6px 18px rgba(156, 115, 54, 0.45);",
    "box-shadow: 0 6px 18px rgba(26, 41, 54, 0.35);"
)

# 5. header background
css = css.replace(
    "border-bottom: 1px solid rgba(230, 230, 227, 0.6); /* Softer border */\n    background: rgba(244, 244, 242, 0.96); /* Slightly more opaque */",
    "border-bottom: 1px solid rgba(255, 255, 255, 0.1);\n    background: rgba(26, 41, 54, 0.90);"
)

# 6. sf-wordmark color
css = css.replace(
    ".sf-wordmark {\n    display: flex;\n    align-items: center;\n    font-family: var(--font-display);\n    font-size: 21px;\n    font-weight: 400; /* Regular for luxury serif */\n    color: var(--charcoal);",
    ".sf-wordmark {\n    display: flex;\n    align-items: center;\n    font-family: var(--font-display);\n    font-size: 21px;\n    font-weight: 400; /* Regular for luxury serif */\n    color: var(--ivory, #f4f4f2);"
)

# 7. sf-nav-link
css = css.replace(
    ".sf-nav-link {\n    position: relative;\n    color: var(--charcoal-soft);",
    ".sf-nav-link {\n    position: relative;\n    color: var(--ivory, #f4f4f2);"
)
css = css.replace(
    ".sf-nav-link:hover, .sf-nav-link:focus-visible, .sf-nav-link.active {\n    color: var(--deep-navy);",
    ".sf-nav-link:hover, .sf-nav-link:focus-visible, .sf-nav-link.active {\n    color: #ffffff;"
)
css = css.replace(
    "background: var(--deep-navy);\n    content: \"\";",
    "background: #ffffff;\n    content: \"\";"
)

# 8. sf-icon-btn
css = css.replace(
    ".sf-icon-btn {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 38px;\n    height: 38px;\n    background: transparent;\n    border: none;\n    cursor: pointer;\n    color: var(--charcoal);",
    ".sf-icon-btn {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 38px;\n    height: 38px;\n    background: transparent;\n    border: none;\n    cursor: pointer;\n    color: var(--ivory, #f4f4f2);"
)
css = css.replace(
    ".sf-icon-btn:hover {\n    color: var(--deep-navy);\n    background: var(--warm-beige, #f9f6f0);",
    ".sf-icon-btn:hover {\n    color: #ffffff;\n    background: rgba(255, 255, 255, 0.1);"
)

with open("static/css/storefront.css", "w") as f:
    f.write(css)

print("Updates applied successfully.")
