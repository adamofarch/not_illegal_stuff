import cv2
import numpy as np
import pytesseract
from PIL import Image
from sympy import sympify

def preprocess_image(image_path):
    """Preprocess the image to enhance OCR accuracy for math expressions."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Experiment with Preprocessing ---
    # Option 1: Adaptive Thresholding (Often better for CAPTCHAs)
    # binary = cv2.adaptiveThreshold(
    #     gray, 255,
    #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # Or cv2.ADAPTIVE_THRESH_MEAN_C
    #     cv2.THRESH_BINARY_INV,
    #     blockSize=15 , # EXPERIMENT
    #     C=4         # EXPERIMENT
    # )

    # Option 2: Simple Global Threshold (Keep your original if it works better sometimes)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # --- Experiment with Noise Removal ---
    # Option A: No blur (might be best)
    # denoised = binary

    # Option B: Median Blur (if needed for salt-pepper noise)
    # denoised = cv2.medianBlur(binary, 3) # Or 1 to disable

    # Option C: Morphological Opening (if needed for thin lines/dots noise)
    kernel = np.ones((2,2),np.uint8) # EXPERIMENT kernel size
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    denoised = opened

    # Invert back to black text on white background for Tesseract
    preprocessed = cv2.bitwise_not(denoised)

    return preprocessed, img

def ocr_math_expression(image_path):
    """Extract math expressions from an image using OCR."""
    try:
        preprocessed, original = preprocess_image(image_path)
    except FileNotFoundError as e:
         print(e)
         return None # Or handle error differently

    # Display images (optional, comment out for non-interactive use)
    # plt.figure(figsize=(12, 6))
    # plt.subplot(1, 2, 1); plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB)); plt.title('Original')
    # plt.subplot(1, 2, 2); plt.imshow(preprocessed, cmap='gray'); plt.title('Preprocessed')
    # plt.show()

    # Save preprocessed image for command-line testing (optional)
    # cv2.imwrite("preprocessed_debug.png", preprocessed)

    pil_img = Image.fromarray(preprocessed)

    # --- Configure Tesseract --- EXPERIMENT HERE ---
    # Common PSM modes for CAPTCHAs: 7, 8, 13
    psm_mode = 7
    # Refined whitelist based on expected characters
    whitelist = "0123456789+-*xX/=" # Adjust if 'x' or '^' etc. are needed

    config = f'--psm {psm_mode} --oem 3 -c tessedit_char_whitelist="{whitelist}"'
    print(f"Using Tesseract config: {config}") # Print config being used

    text = pytesseract.image_to_string(pil_img, config=config)
    print(f"Raw Tesseract Output: '{text}'") # Crucial for debugging

    # Basic cleaning - removing control characters and stripping whitespace
    cleaned_text = ''.join(char for char in text if char.isprintable() or char.isspace())
    cleaned_text = cleaned_text.strip()
    # Remove spaces - common/often needed for simple math CAPTCHAs
    cleaned_text = cleaned_text.replace(' ', '')

    # Handle potential empty output
    if not cleaned_text:
        print("Warning: OCR resulted in empty string.")
        return ""

    return cleaned_text
def process_math_expression(expression):
    """Process and evaluate the math expression."""
    if not expression:
         return "Cannot process empty expression."
    try:
        # Common OCR error replacements
        proc_expr = expression.replace('S', '5').replace('O', '0').replace('l', '1').replace('Z', '2')
        proc_expr = proc_expr.replace('?', '7') # Add more if needed
        proc_expr = proc_expr.replace(' ', '') # Remove spaces again if not done in OCR
        
        # print(len(proc_expr))

        # if len(expression) == 2:
        #     proc_expr = proc_expr[0] + 'x' + proc_expr[1] 
        if proc_expr[1] == '4':
            proc_expr = proc_expr.replace('4', '+')

        # Replace visual multiplication ('x' or 'X') with '*' if necessary
        proc_expr = proc_expr.replace('x', '*').replace('X', '*')

        # Ensure expression isn't just operators or invalid start/end
        if not any(char.isdigit() for char in proc_expr):
             raise ValueError("Expression contains no digits")
        if proc_expr.startswith(('*', '/')) or proc_expr.endswith(('*', '/', '+', '-')):
             raise ValueError("Expression has leading/trailing operator")

        # Use sympy to safely evaluate the expression
        result = sympify(proc_expr, evaluate=True) # evaluate=True simplifies directly
        # Check if result is symbolic or numerical
        if result.is_Atom and not result.is_symbol:
             # Use evalf for potentially higher precision if needed, or just str(result)
             return f"Expression: {proc_expr}\nResult: {result}"
        else:
             # Handle cases where sympify returns a symbolic expression if evaluate=False or fails
             return f"Expression: {proc_expr}\nSymbolic Result: {result}"


    except (SyntaxError, TypeError, ValueError, Exception) as e:
        return f"Failed to evaluate expression: '{expression}' (processed as '{proc_expr}'). Error: {type(e).__name__} - {str(e)}"

def main():
    image_path = "captcha.png"

    # Extract the math expression from the image
    extracted_text = ocr_math_expression(image_path)
    print(f"Extracted text: {extracted_text}")

    # Process and evaluate the expression
    result = process_math_expression(extracted_text)
    print(result)

if __name__ == "__main__":
    main()
