import cv2
import numpy as np
import pandas as pd
import pyautogui
from PIL import Image, ImageTk
from pytesseract import image_to_data, pytesseract
import tkinter as tk
from tkinter import messagebox

pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class RegionSelector(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Select Screenshot Region")

        self.screenshot = None
        self.region = (0, 0, 0, 0)

        self.canvas = tk.Canvas(self, width=300, height=300, bg="white")
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_button_motion)
        self.bind("<ButtonRelease-1>", self.on_button_release)

        self.rect = None

    def on_button_press(self, event):
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None

        self.start_x = event.x
        self.start_y = event.y

    def on_button_motion(self, event):
        if self.rect:
            self.canvas.delete(self.rect)

        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def on_button_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.region = (self.start_x, self.start_y, self.end_x, self.end_y)
        self.capture_screenshot()

    def capture_screenshot(self):
        self.screenshot = pyautogui.screenshot(region=self.region)
        self.screenshot = cv2.cvtColor(np.array(self.screenshot), cv2.COLOR_RGB2BGR)
        self.quit()


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

        table_data['text'] = table_data['text'].astype(str)  # Add this line to convert the text column to strings
        table = pd.DataFrame(table_data.groupby(['block_num', 'par_num', 'line_num', 'word_num'])['text'].apply(' '.join).reset_index())
        table = table.pivot_table(values='text', index=['block_num', 'par_num', 'line_num'], columns=['word_num'], aggfunc='first').reset_index(drop=True)
        mode = 'a' if append_mode else 'w'
        table.to_csv(output_file, sep='\t', index=False, header=not append_mode, mode=mode)
    except Exception as e:
        print("Error transcribing table:", e)

def main():
    app = RegionSelector()
    app.mainloop()

    screenshot = app.screenshot
    if screenshot is None:
        messagebox.showerror("Error", "Unable to capture a screenshot.")
        return

    tables = detect_tables(screenshot)
    if not tables:
        messagebox.showerror("Error", "No tables detected.")
        return

    output_file = 'output.tsv'
    append_mode = False

    for table_contour in tables:
        table_to_tsv(screenshot, table_contour, output_file, append_mode)
        append_mode = True

    messagebox.showinfo("Success", "Table transcription completed. Data saved to output.tsv.")

if __name__ == '__main__':
    main()
