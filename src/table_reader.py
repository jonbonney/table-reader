import cv2
import numpy as np
import pandas as pd
from mss import mss
from PIL import Image, ImageTk
from pytesseract import image_to_data, pytesseract
import tkinter as tk
from tkinter import messagebox
import os

pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class RegionSelector(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Select Screenshot Region")
        self.attributes('-alpha', 0.3)  # Set the window opacity to 0.3
        self.attributes('-fullscreen', True)  # Make the window fullscreen

        self.screenshot = None
        self.region = (0, 0, 0, 0)

        # Set the canvas size to the screen size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Create a transparent canvas
        self.canvas = tk.Canvas(self, width=screen_width, height=screen_height, bg="white")
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
        region = {
            "top": self.start_y,
            "left": self.start_x,
            "width": abs(self.end_x - self.start_x),
            "height": abs(self.end_y - self.start_y),
        }

        with mss() as sct:
            self.screenshot = sct.grab(region)
            self.screenshot = np.array(self.screenshot)
            self.screenshot = cv2.cvtColor(self.screenshot, cv2.COLOR_RGBA2BGR)
            self.quit()



class ImageSaver:
    def __init__(self, images, output_folder="output"):
        self.images = images
        self.output_folder = output_folder

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        self.save_images()

    def save_images(self):
        for index, (label, image) in enumerate(self.images):
            output_path = os.path.join(self.output_folder, f"{label}.png")
            image = Image.fromarray(image)
            image.save(output_path)


def detect_tables(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ocr_data = image_to_data(gray, output_type='data.frame')
        ocr_data = ocr_data[(ocr_data.conf != '-1') & (ocr_data.text != '')]
        return gray, ocr_data
    except Exception as e:
        print("Error detecting tables:", e)
        return [], []




def table_to_tsv(ocr_data, output_file, append_mode=False):
    try:
        if len(ocr_data) == 0:
            print("Warning: OCR results may not be satisfactory.")
            return

        ocr_data['text'] = ocr_data['text'].astype(str)  # Convert the text column to strings
        table = pd.DataFrame(ocr_data.groupby(['block_num', 'par_num', 'line_num', 'word_num'])['text'].apply(' '.join).reset_index())
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

    gray, ocr_data = detect_tables(screenshot)

    if ocr_data.empty:
        messagebox.showerror("Error", "No tables detected.")
        return

    output_file = 'output.tsv'
    append_mode = False
    error_occurred = False

    processed_images = [
        ('Original Image', cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)),
        ('Gray Image', cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)),
    ]
    try:
        table_to_tsv(ocr_data, output_file, append_mode)
    except Exception as e:
        print("Error transcribing table:", e)
        error_occurred = True  # Set the error flag if an exception occurs

    if not processed_images:
        messagebox.showerror("Error", "No processed images to display.")
    else:
        image_saver = ImageSaver(processed_images)

    if error_occurred:
        messagebox.showerror("Error", "An error occurred during table transcription. Check the console for more details.")
    else:
        messagebox.showinfo("Success", "Table transcription completed. Data saved to output.tsv.")


if __name__ == '__main__':
    main()
