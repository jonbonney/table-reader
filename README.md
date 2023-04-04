# table-reader
 transcribe tables currently displayed on the screen

Follow these steps to install Tesseract and add it to your PATH:

Install Tesseract OCR:

macOS: Use Homebrew to install Tesseract by running brew install tesseract.
Windows: Download the installer from https://github.com/UB-Mannheim/tesseract/wiki and run the installation process. During installation, make sure to select the option to add Tesseract to the system PATH.
Linux (Debian/Ubuntu): Run sudo apt-get install tesseract-ocr.
Add Tesseract OCR to your system's PATH:

macOS and Linux: Typically, the Tesseract executable should already be in your system's PATH after installation. If it's not, find the installation path (e.g., /usr/local/bin/tesseract for macOS) and add it to your PATH in your shell profile (e.g., ~/.bashrc, ~/.bash_profile, or ~/.zshrc).
Windows: The installer should have added Tesseract to the PATH automatically. If it's not, locate the installation folder (e.g., C:\Program Files\Tesseract-OCR) and add the folder containing the tesseract.exe file to your system's PATH in the Environment Variables settings.
After completing the installation and adding Tesseract to your PATH, restart your Python script, and the error should be resolved.
