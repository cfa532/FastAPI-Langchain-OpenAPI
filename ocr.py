from tempfile import TemporaryDirectory, NamedTemporaryFile
# import textract
import pytesseract, os
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image

# convert PDF page to image, then run OCR to recognize Simplified Chinese
def load_pdf(pdf):
    # extract text from a pdf BYTEs object

    os.environ["TESSDATA_PREFIX"]= os.getcwd() + "/tessdata"
    text = ""
    with TemporaryDirectory() as tempdir:
        # create temp dir to hold temporary images
        pdf_pages = convert_from_bytes(pdf, 200)
        # Read in the PDF file at 500 DPI
        for num, page in enumerate(pdf_pages, start=1):
            img = f"{tempdir}\page_{num:03}.jpg"
            page.save(img, "JPEG")
            text += str(pytesseract.image_to_string(Image.open(img), lang="chi_sim"))
        text = text.replace("-\n", "").replace(" ", "")
        return text


"""
def load_doc(doc: bytes):
    # does not work for DOC file
    text = ""
    temp = NamedTemporaryFile()
    try:
        temp.write(doc)
        text = textract.process(temp.name)
    finally:
        temp.close()
    return text
"""
