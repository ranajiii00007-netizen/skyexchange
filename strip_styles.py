import glob, os, re

files = glob.glob("pages/*.py")
pattern = re.compile(r'\s*style\s*=\s*ttk\.Style\(\)\s*\n\s*style\.theme_use\("clam"\)\s*\n\s*style\.configure\("Treeview".*?\n\s*style\.configure\("Treeview\.Heading".*?\n', re.MULTILINE | re.DOTALL)

for f in files:
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    new_content, count = pattern.subn("", content)
    if count > 0:
        with open(f, "w", encoding="utf-8") as file:
            file.write(new_content)
        print(f"Removed {count} overrides from {f}")
