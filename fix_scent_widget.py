import re

with open("static/css/storefront.css", "r") as f:
    css = f.read()

# 1. Widget background
css = css.replace(
    ".scent-finder-widget {\n    background: linear-gradient(165deg, rgba(26, 41, 54, 0.03) 0%, rgba(26, 41, 54, 0.1) 100%);\n    backdrop-filter: blur(8px);\n    -webkit-backdrop-filter: blur(8px);\n    border: 1px solid rgba(26, 41, 54, 0.15);\n    border-radius: var(--radius-sm, 6px);\n    padding: 20px 18px;\n    margin-bottom: 32px;\n    box-shadow: 0 4px 20px rgba(74, 52, 33, 0.05);",
    ".scent-finder-widget {\n    background: #e6f0fa;\n    border: 1px solid #c9def0;\n    border-radius: var(--radius-sm, 6px);\n    padding: 20px 18px;\n    margin-bottom: 32px;\n    box-shadow: 0 4px 20px rgba(26, 41, 54, 0.08);"
)

# 2. Status badge (active / edit)
css = css.replace(
    "color: #8c6a38;\n    background: #fdf5e6;\n    border: 1px solid #e8decb;",
    "color: #ffffff;\n    background: #0f4c81;\n    border: 1px solid #0f4c81;"
)

# 3. Chevron color
css = css.replace(
    ".scent-finder-chevron {\n    font-size: 11px;\n    color: #8c8172;",
    ".scent-finder-chevron {\n    font-size: 11px;\n    color: #1a2936;"
)

# 4. Eyebrow color (gold -> popping color, e.g. bright orange or blue. Let's use #0f4c81)
css = css.replace(
    ".scent-finder-eyebrow {\n    font-size: 10px;\n    letter-spacing: 0.15em;\n    text-transform: uppercase;\n    color: #926f34;",
    ".scent-finder-eyebrow {\n    font-size: 10px;\n    letter-spacing: 0.15em;\n    text-transform: uppercase;\n    color: #0f4c81;"
)

# 5. Titles and descriptions (warm greys -> dark blues)
css = css.replace(
    ".scent-finder-title {\n    font-family: var(--font-display, serif);\n    font-size: 22px;\n    color: var(--charcoal, #1f1b18);",
    ".scent-finder-title {\n    font-family: var(--font-display, serif);\n    font-size: 22px;\n    color: #1a2936;"
)
css = css.replace(
    "color: #6d645a;",
    "color: #3b5063;"
)

# 6. Purpose Tabs background and border
css = css.replace(
    "background: rgba(220, 210, 191, 0.35);\n    padding: 4px;\n    border-radius: 4px;\n    margin-bottom: 20px;\n    border: 1px solid rgba(210, 198, 175, 0.6);",
    "background: rgba(26, 41, 54, 0.08);\n    padding: 4px;\n    border-radius: 4px;\n    margin-bottom: 20px;\n    border: 1px solid rgba(26, 41, 54, 0.1);"
)
css = css.replace(
    "color: #5a5146;",
    "color: #2b3d4f;"
)
css = css.replace(
    ".scent-purpose-tab.is-active {\n    background: var(--deep-navy, #1a2936);\n    color: var(--ivory, #f4f4f2);\n    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);\n    font-weight: 700;\n    border: 1px solid #d4c7b0;",
    ".scent-purpose-tab.is-active {\n    background: var(--deep-navy, #1a2936);\n    color: #ffffff;\n    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);\n    font-weight: 700;\n    border: 1px solid var(--deep-navy, #1a2936);"
)

# 7. Group border
css = css.replace(
    "border-bottom: 1px solid rgba(220, 210, 191, 0.5);",
    "border-bottom: 1px solid rgba(26, 41, 54, 0.15);"
)

# 8. Radio/Checkbox styles
css = css.replace(
    "color: #2e261f;",
    "color: #1a2936;"
)
css = css.replace(
    "color: #403831;",
    "color: #2b3d4f;"
)
css = css.replace(
    "accent-color: #9c7336;",
    "accent-color: #0f4c81;"
)

# 9. Pills
css = css.replace(
    "background: #ffffff;\n    border: 1px solid #dcd2bf;",
    "background: #ffffff;\n    border: 1px solid #bcd1e6;"
)
css = css.replace(
    "color: #544a40;",
    "color: #2b3d4f;"
)
css = css.replace(
    "border-color: #9c7336;\n    color: #1a1613;\n    background: #fdfaf3;",
    "border-color: #0f4c81;\n    color: #1a2936;\n    background: #eef5fb;"
)
css = css.replace(
    ".scent-pill-label:has(input:checked) {\n    background: #2a2016;\n    color: #f7eedb;\n    border-color: #2a2016;",
    ".scent-pill-label:has(input:checked) {\n    background: #1a2936;\n    color: #ffffff;\n    border-color: #1a2936;"
)
css = css.replace(
    "box-shadow: 0 2px 5px rgba(42, 32, 22, 0.2);",
    "box-shadow: 0 2px 5px rgba(26, 41, 54, 0.2);"
)

# 10. Reset Link
css = css.replace(
    "color: #8c8172;",
    "color: #3b5063;"
)
css = css.replace(
    ".scent-quiz-reset-link:hover {\n    color: #2a2016;\n}",
    ".scent-quiz-reset-link:hover {\n    color: #1a2936;\n}"
)

with open("static/css/storefront.css", "w") as f:
    f.write(css)

print("CSS widget updated to blue!")
