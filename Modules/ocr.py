from PIL import Image
import pytesseract


# ✅ Make sure this path includes the tesseract.exe at the end
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load your image
image = Image.open('testocr.png')

# Extract text
#text = pytesseract.image_to_string(image)
#print("Extracted Text:")
#print(text)

# Highlightable PNG after converting to PDF
pdf_bytes = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')
# Save to file
with open('output.pdf', 'wb') as f:
    f.write(pdf_bytes)
