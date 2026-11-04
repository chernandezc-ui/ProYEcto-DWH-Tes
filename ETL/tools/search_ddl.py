import os
import re

def search_text(pattern, root_dir):
    regex = re.compile(pattern, re.IGNORECASE)
    for root, dirs, files in os.walk(root_dir):
        # Evitar carpetas virtuales/venv
        if '.venv' in root or '.git' in root or '.obsidian' in root:
            continue
        for file in files:
            if file.endswith(('.sql', '.md', '.py')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, start=1):
                            if regex.search(line):
                                print(f"{path}:{i} -> {line.strip()}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    print("=== BUSCANDO Fact_Tasa_Crecimiento_Brotes ===")
    search_text("Fact_Tasa_Crecimiento_Brotes", ".")
