from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from tkinter import filedialog as fd
import os
import shutil
import re
from PyPDF2 import PdfFileWriter, PdfFileReader
import numpy as np
import cv2


image_dir = "image_pages"
text_dir = "text"
pdf_dir = "pdf_files"


def open_file():
    global PDF_file
    PDF_file = fd.askopenfilename()


def pdf_to_image():
    global image_counter
    image_counter = 0
    pages = convert_from_path(
        PDF_file,
        300,
        poppler_path="poppler-0.68.0\\bin",
        grayscale=True,
        use_pdftocairo=True,
        use_cropbox=True
    )

    for page in pages:
        filename = "image_pages/" + str(image_counter) + ".jpg"
        page.save(filename, 'JPEG')
        image_counter += 1


def improve_ocr_algorithm(image):
    gaussian = cv2.GaussianBlur(image, (9, 9), 10)
    image = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0, image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated


def improve_ocr():
    for i in absolute_file_paths(image_dir):
        image = cv2.imread(i)
        cv2.imwrite(i, improve_ocr_algorithm(image))


def absolute_file_paths(directory):
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))


def get_image_list():
    global image_files
    global image_dir
    image_files = []

    for i in absolute_file_paths(image_dir):
        image_files.append(i)


def ocr():
    pytesseract.pytesseract.tesseract_cmd = r'Tesseract-OCR\\tesseract.exe'

    for i in range(len(image_files)):
        filename = "image_pages/" + str(i) + ".jpg"

        with open("text/{:03d}.txt".format(i), "a") as f:
            text = str((pytesseract.image_to_string(Image.open(filename), lang="rus")))
            text = text.replace('-\n', '')
            f.write(text)


def get_text_files_list():
    global text_files
    global text_dir
    text_files = []

    for i in absolute_file_paths(text_dir):
        text_files.append(i)


def get_split_keyword():
    global first_pages
    first_pages = []

    for file in text_files:
        with open(file) as f:
            file_reader = f.read()
            if re.search("УСТАНОВИЛ", file_reader):
                first_pages.append(file)
            elif re.search("установил", file_reader):
                first_pages.append(file)


def get_pages_number_list(files):
    global keyword_numbers
    keyword_numbers = []

    for i in files:
        number = re.search("\d\d\d.txt", i).group(0)
        number.replace(".txt", " ")
        number = re.search("\d\d\d", number).group(0)
        number = int(number)
        keyword_numbers.append(number)


def get_document_number(files):
    global document_numbers_fixed
    document_numbers = []
    document_numbers_fixed = []
    counter = 0

    for file in files:
        with open(file) as f:
            file = f.read()
            if re.search("№ \d+/\d\d/\d+-", file):
                document_numbers.append(re.search("№ \d+/\d\d/\d+-", file).group(0))
            else:
                document_numbers.append("Не удалось найти номер (" + str(counter) + ")")
                counter += 1

    for number in document_numbers:
        number = "pdf_files\\" + number + ".pdf"
        number = number.replace("-", "")
        number = number.replace("/", "-")
        document_numbers_fixed.append(number)


def split():
    f = PdfFileReader(open(PDF_file, 'rb'))
    keyword_numbers.append(f.numPages)

    last_index = 0
    counter = 0

    for i in keyword_numbers:
        output = PdfFileWriter()
        if i == last_index:
            continue
        for page in range(last_index, i):
            output.addPage(f.getPage(page))

        with open(document_numbers_fixed[counter], "wb") as outputStream:
            output.write(outputStream)

        counter += 1

        last_index = i


def get_pdf_files():
    global pdf_files
    pdf_files = []

    for i in absolute_file_paths(pdf_dir):
        pdf_files.append(i)


def clear_directories(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete {0}. Reason: {1}'.format(file_path, e))


if __name__ == '__main__':
    try:
        open_file()
        pdf_to_image()
        improve_ocr()
        get_image_list()
        ocr()
        get_text_files_list()
        get_split_keyword()
        get_pages_number_list(first_pages)
        get_document_number(first_pages)
        split()
        get_pdf_files()
    except Exception as exception:
        # with open("error.log", "w") as error_file:
        #     error_file.write(str(exception))
        pass
    # finally:
    #     clear_directories(image_dir)
    #     clear_directories(text_dir)
