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
        self.attributes('-alpha', 0.1)  # Set the window opacity to 0.3
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


class ColumnSelector(tk.Toplevel):
    def __init__(self, image, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Select Column Boundaries")
        self.column_lines = []

        self.image = ImageTk.PhotoImage(Image.fromarray(image))
        self.canvas = tk.Canvas(self, width=self.image.width(), height=self.image.height())
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image)

        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_button_motion)
        self.bind("<ButtonRelease-1>", self.on_button_release)

        self.done_button = tk.Button(self, text="Done", command=self.finish_column_selection)
        self.done_button.pack(side=tk.BOTTOM)

        self.line = None

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_button_motion(self, event):
        if self.line:
            self.canvas.delete(self.line)

        self.line = self.canvas.create_line(self.start_x, self.start_y, event.x, self.start_y, fill="black", width=5)

    def on_button_release(self, event):
        self.end_x = event.x
        self.canvas.delete(self.line)
        self.line = None

        if abs(self.start_x - self.end_x) < 5:  # Change this value to adjust the sensitivity of detecting a move
            # If the mouse hasn't moved, create a new column boundary
            line = self.canvas.create_line(self.start_x, 0, self.start_x, self.image.height(), fill="red")
            self.column_lines.append((self.start_x, line))
        else:
            # If the mouse has moved, delete all columns between the two coordinates
            for x, line in self.column_lines:
                if min(self.start_x, self.end_x) <= x <= max(self.start_x, self.end_x):
                    self.canvas.delete(line)
                    self.column_lines.remove((x, line))

    def finish_column_selection(self):
        self.quit()


def screenshot_to_data(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ocr_data = image_to_data(gray, output_type='data.frame')
        ocr_data = ocr_data[(ocr_data.conf != -1) & (ocr_data.text != '')]
        ocr_data.reset_index(drop=True, inplace=True)
        ocr_data['right'] = ocr_data['left'] + ocr_data['width']
        ocr_data.sort_values(by=['top', 'left'])
        ocr_data.to_csv("ocr_data.tsv", sep='\t')
        return ocr_data
    except Exception as e:
        print("Error detecting tables:", e)
        return
    

def data_to_table(ocr_data, column_coords):
    table = pd.DataFrame()
    row_iter = 0
    col_iter = 0
    row_thresh = 10
    col_thresh = 10
    prev_column_rows_top = []

    for index, row in ocr_data.iterrows():
        if index == 0:
            print('Parsing text data...')
            cell = [row['text']]
            prev_row = row
            continue

        in_same_cell = (row['top'] <= prev_row['top'] + row_thresh) and (0 < row['left'] - prev_row['right'] < col_thresh)
        in_new_column = any([abs(row['left'] - col_x) < col_thresh for col_x in column_coords])

        if in_same_cell and not in_new_column:
            cell.append(row['text'])
        else:
            cell = ' '.join(cell)
            table.at[row_iter, col_iter] = cell

            if row['top'] - prev_row['top'] > row_thresh:
                row_iter += 1
                col_iter = 0
                prev_column_rows_top.append(prev_row['top'])
            else:
                col_iter += 1

            if col_iter >= len(column_coords):
                col_iter = 0

            # Find the correct row for the current cell using the 'top' values of the previous column's rows
            if col_iter > 0:
                min_diff = float('inf')
                closest_row = row_iter
                for i, prev_top in enumerate(prev_column_rows_top):
                    diff = abs(row['top'] - prev_top)
                    if diff < min_diff:
                        min_diff = diff
                        closest_row = i
                row_iter = closest_row

            cell = [row['text']]
        prev_row = row

    cell = ' '.join(cell)
    table.at[row_iter, col_iter] = cell

    print(table.head())
    return table


def main():
    app = RegionSelector()
    app.mainloop()

    screenshot = app.screenshot
    if screenshot is None:
        messagebox.showerror("Error", "Unable to capture a screenshot.")
        return

    col_selector = ColumnSelector(screenshot)
    col_selector.mainloop()

    column_coords = sorted(x for x, _ in col_selector.column_lines)

    image = Image.fromarray(screenshot)
    image.save('output/image.png')
    ocr_data = screenshot_to_data(screenshot)
    print(ocr_data.head())

    if ocr_data.empty:
        messagebox.showerror("Error", "No tables detected.")
        return

    output_file = 'output.tsv'
    error_occurred = False

    try:
        # Read the existing data
        if os.path.exists(output_file):
            existing_data = pd.read_csv(output_file, sep='\t', header=None)
        else:
            existing_data = pd.DataFrame()

        # Get the new table data
        new_table = data_to_table(ocr_data, column_coords)

        # Concatenate the existing data with the new table data
        # combined_data = pd.concat([existing_data, new_table], axis=0, ignore_index=True)
        combined_data = new_table
        # Save the combined data
        combined_data.to_csv(output_file, sep='\t', index=False, header=False)
    except Exception as e:
        print("Error transcribing table:", e)
        error_occurred = True

    if error_occurred:
        messagebox.showerror("Error", "An error occurred during table transcription. Check the console for more details.")
    else:
        messagebox.showinfo("Success", "Table transcription completed. Data saved to output.tsv.")


if __name__ == '__main__':
    main()
