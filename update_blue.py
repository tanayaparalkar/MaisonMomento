import re

# Update dashboard.css
with open("dashboard/static/dashboard/css/dashboard.css", "r") as f:
    dashboard_css = f.read()

dashboard_css = dashboard_css.replace("--deep-navy: #183f6b;", "--deep-navy: #112a3d;")

with open("dashboard/static/dashboard/css/dashboard.css", "w") as f:
    f.write(dashboard_css)

# Update storefront.css
with open("static/css/storefront.css", "r") as f:
    storefront_css = f.read()

storefront_css = storefront_css.replace("#183f6b", "#112a3d")
storefront_css = storefront_css.replace("rgba(24, 63, 107", "rgba(17, 42, 61")

with open("static/css/storefront.css", "w") as f:
    f.write(storefront_css)

print("Colors updated to #112a3d!")
