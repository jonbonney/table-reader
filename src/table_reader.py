import cv2
import numpy as np
import pandas as pd
import pyautogui
from PIL import Image
from pytesseract import image_to_data

def capture_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return screenshot
    except Exception as e:
        print("Error capturing screenshot:", e)
        return None

def detect_tables(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
        dilation = cv2.dilate(thresh, rect_kernel, iterations=1)
        contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    except Exception as e:
        print("Error detecting tables:", e)
        return []

def table_to_tsv(image, table_contour, output_file, append_mode=False):
    try:
        x, y, w, h = cv2.boundingRect(table_contour)
        table_image = image[y:y+h, x:x+w]
        table_data = image_to_data(table_image, output_type='data.frame')
        table_data = table_data[(table_data.conf != '-1') & (table_data.text != '')]

        if len(table_data) == 0:
            print("Warning: OCR results may not be satisfactory.")
            return

        table = pd.DataFrame(table_data.groupby(['block_num', 'par_num', 'line_num', 'word_num'])['text'].apply(' '.join).reset_index())
        table = table.pivot_table(values='text', index=['block_num', 'par_num', 'line_num'], columns=['word_num'], aggfunc='first').reset_index(drop=True)
        mode = 'a' if append_mode else 'w'
        table.to_csv(output_file, sep='\t', index=False, header=not append_mode, mode=mode)
    except Exception as e:
        print("Error transcribing table:", e)

def main():
    screenshot = capture_screenshot()
    if screenshot is None:
        print("Unable to capture a screenshot. Exiting.")
        return

    tables = detect_tables(screenshot)
    if not tables:
        print("No tables detected. Exiting.")
        return

    output_file = 'output.tsv'
    append_mode = False

    for table_contour in tables:
        table_to_tsv(screenshot, table_contour, output_file, append_mode)
        append_mode = True

if __name__ == '__main__':
    main()
