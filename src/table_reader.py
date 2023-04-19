import cv2
import numpy as np
import pandas as pd
import pyautogui
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
        self.screenshot = pyautogui.screenshot(region=self.region)
        self.screenshot = cv2.cvtColor(np.array(self.screenshot), cv2.COLOR_RGB2BGR)
        self.quit()
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
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
        dilation = cv2.dilate(thresh, rect_kernel, iterations=1)
        contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return gray, thresh, dilation, contours
    except Exception as e:
        print("Error detecting tables:", e)
        return [], [], [], []



def table_to_tsv(image, table_contour, output_file, append_mode=False):
    processed_images = []
    try:
        x, y, w, h = cv2.boundingRect(table_contour)
        table_image = image[y:y+h, x:x+w]
        processed_images.append(('Table Image', cv2.cvtColor(table_image, cv2.COLOR_BGR2RGB)))
        table_data = image_to_data(table_image, output_type='data.frame')
        table_data = table_data[(table_data.conf != '-1') & (table_data.text != '')]

        if len(table_data) == 0:
            print("Warning: OCR results may not be satisfactory.")
            return processed_images

        table_data['text'] = table_data['text'].astype(str)  # Add this line to convert the text column to strings
        table = pd.DataFrame(table_data.groupby(['block_num', 'par_num', 'line_num', 'word_num'])['text'].apply(' '.join).reset_index())
        table = table.pivot_table(values='text', index=['block_num', 'par_num', 'line_num'], columns=['word_num'], aggfunc='first').reset_index(drop=True)
        mode = 'a' if append_mode else 'w'
        table.to_csv(output_file, sep='\t', index=False, header=not append_mode, mode=mode)
    except Exception as e:
        print("Error transcribing table:", e)

    return processed_images


def main():
    app = RegionSelector()
    app.mainloop()

    screenshot = app.screenshot
    if screenshot is None:
        messagebox.showerror("Error", "Unable to capture a screenshot.")
        return

    gray, thresh, dilation, tables = detect_tables(screenshot)

    if not tables:
        messagebox.showerror("Error", "No tables detected.")
        return

    output_file = 'output.tsv'
    append_mode = False
    error_occurred = False

    processed_images = [
        ('Original Image', cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)),
        ('Gray Image', cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)),
        ('Thresh Image', cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)),
        ('Dilation Image', cv2.cvtColor(dilation, cv2.COLOR_GRAY2RGB)),
    ]
    for table_contour in tables:
        try:
            table_images = table_to_tsv(screenshot, table_contour, output_file, append_mode)
            processed_images.extend(table_images)
            append_mode = True
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
