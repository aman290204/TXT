import base64

encoded = "LzRiMDZiZjhkNjFjNDFmODMxMGFmOWIyNjI0NDU5Mzc4MjAzNzQwOTMyYjQ1NmIwN2ZjZjgxN2I3MzdmYmFlMjcveUNsMGVKSUouanBlZw=="
try:
    decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore')
    print(f"Decoded: {decoded}")
except Exception as e:
    print(f"Error: {e}")
