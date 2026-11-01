with open('backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def serve_index():')
print("Index of def serve_index():", idx)
if idx != -1:
    print(text[idx:idx+400])
