import pdfplumber

with pdfplumber.open('Formato Cotización 2026.pdf') as pdf:
    page = pdf.pages[0]
    
    # Extraer texto
    print("=== CONTENIDO DE TEXTO ===")
    text = page.extract_text()
    print(text)
    
    print("\n=== DIMENSIONES ===")
    print(f"Ancho: {page.width}, Alto: {page.height}")
    
    # Extraer tablas
    print("\n=== TABLAS ===")
    tables = page.extract_tables()
    print(f"Número de tablas: {len(tables)}")
    for i, table in enumerate(tables):
        print(f"\nTabla {i} ({len(table)} filas):")
        for row in table[:5]:
            print(row)
