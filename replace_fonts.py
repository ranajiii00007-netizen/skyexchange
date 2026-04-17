import glob, os

files = glob.glob('pages/*.py')
# Replace hardcoded Segoe UI fonts with AppStyles fonts
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Simple replace for common hardcoded fonts
    content = content.replace('font=("Segoe UI", 9)', 'font=styles.AppStyles.FONTS["body"]')
    content = content.replace('font=("Segoe UI", 8)', 'font=styles.AppStyles.FONTS["small"]')
    content = content.replace('font=("Segoe UI", 10, "bold")', 'font=styles.AppStyles.FONTS["heading"]')
    content = content.replace('font=("Segoe UI", 9, "bold")', 'font=styles.AppStyles.FONTS["body_bold"]')
    content = content.replace('font=("Segoe UI", 11, "bold")', 'font=styles.AppStyles.FONTS["subtitle"]')
    content = content.replace('font=("Segoe UI", 12, "bold")', 'font=styles.AppStyles.FONTS["subtitle"]')
    content = content.replace('font=("Segoe UI", 14, "bold")', 'font=styles.AppStyles.FONTS["title"]')
    content = content.replace('font=("Segoe UI", 10)', 'font=styles.AppStyles.FONTS["body"]')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Replaced fonts in {f}")
