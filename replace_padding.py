import glob, os

files = glob.glob('pages/*.py')
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Increase the padding around items
    content = content.replace('pady=3', 'pady=6')
    content = content.replace('pady=5', 'pady=10')
    content = content.replace('pady=(10, 5)', 'pady=(15, 10)')
    content = content.replace('padx=(0, 15)', 'padx=(10, 25)')
    content = content.replace('padx=(0, 12)', 'padx=(10, 20)')
    content = content.replace('padx=(0, 3)', 'padx=(5, 8)')
    content = content.replace('padx=(0, 8)', 'padx=(5, 12)')
    content = content.replace('padx=8', 'padx=12')
    content = content.replace('padx=5', 'padx=10')
    content = content.replace('pady=(0, 8)', 'pady=(5, 12)')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Replaced paddings in {f}")
