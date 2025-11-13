import os

# Carpeta raíz del proyecto
root_dir = os.path.dirname(os.path.abspath(__file__))

for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith('.py'):
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                # Elimina bytes nulos
                clean_content = content.replace(b'\x00', b'')
                with open(file_path, 'wb') as f:
                    f.write(clean_content)
                print(f"[OK] Limpiado: {file_path}")
            except Exception as e:
                print(f"[ERROR] {file_path} → {e}")
