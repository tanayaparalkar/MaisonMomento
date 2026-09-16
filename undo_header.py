import re

with open("static/css/storefront.css", "r") as f:
    css = f.read()

# 5. header background
css = css.replace(
    "border-bottom: 1px solid rgba(255, 255, 255, 0.1);\n    background: rgba(26, 41, 54, 0.90);",
    "border-bottom: 1px solid rgba(230, 230, 227, 0.6); /* Softer border */\n    background: rgba(244, 244, 242, 0.96); /* Slightly more opaque */"
)

# sf-brand color
css = css.replace(
    ".sf-brand {\n    display: flex;\n    align-items: center;\n    gap: 14px; /* More spacing */\n    color: var(--ivory, #f4f4f2);",
    ".sf-brand {\n    display: flex;\n    align-items: center;\n    gap: 14px; /* More spacing */\n    color: var(--charcoal);"
)

# 7. sf-nav-link
css = css.replace(
    ".sf-nav-link {\n    position: relative;\n    color: var(--ivory, #f4f4f2);",
    ".sf-nav-link {\n    position: relative;\n    color: var(--charcoal-soft);"
)
css = css.replace(
    ".sf-nav-link:hover, .sf-nav-link:focus-visible, .sf-nav-link.active {\n    color: #ffffff;",
    ".sf-nav-link:hover, .sf-nav-link:focus-visible, .sf-nav-link.active {\n    color: var(--deep-navy);"
)
css = css.replace(
    "background: #ffffff;\n    content: \"\";",
    "background: var(--deep-navy);\n    content: \"\";"
)

# 8. sf-icon-btn
css = css.replace(
    ".sf-icon-btn {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 38px;\n    height: 38px;\n    background: transparent;\n    border: none;\n    cursor: pointer;\n    color: var(--ivory, #f4f4f2);",
    ".sf-icon-btn {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 38px;\n    height: 38px;\n    background: transparent;\n    border: none;\n    cursor: pointer;\n    color: var(--charcoal);"
)
css = css.replace(
    ".sf-icon-btn:hover {\n    color: #ffffff;\n    background: rgba(255, 255, 255, 0.1);",
    ".sf-icon-btn:hover {\n    color: var(--deep-navy);\n    background: var(--warm-beige, #f9f6f0);"
)

with open("static/css/storefront.css", "w") as f:
    f.write(css)

print("Updates applied successfully.")
