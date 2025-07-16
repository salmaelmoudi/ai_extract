from extractor.extractor_router import extract_text_from_pdf, extract_entities

# Met le chemin vers un fichier PDF test
pdf_path = "temp/facture_test.pdf"  # Assure-toi que ce fichier existe dans ce dossier

# OCR + extraction
texte = extract_text_from_pdf(pdf_path)
infos = extract_entities(texte)

# Affichage
for clé, valeur in infos.items():
    print(f"{clé} : {valeur}")
