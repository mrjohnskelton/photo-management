import boto3
import io
from pathlib import Path
import os
import configparser
from PIL import Image, UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.utils import ImageReader
import logging
import re # For sanitizing filename
from collections import defaultdict
import math

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'config.ini'
VALID_JPEG_EXTENSIONS = {'.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi', '.JPG', '.JPEG', '.JPE'}

# --- Helper Functions ---

def read_config(filename=CONFIG_FILE):
    """Reads configuration from the INI file."""
    config = configparser.ConfigParser()
    script_dir = Path(__file__).resolve().parent
    filename = script_dir / filename
    if not os.path.exists(filename):
        logging.error(f"Configuration file '{filename}' not found.")
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    config.read(filename)
    try:
        s3_config = config['S3']
        layout_config = config['Layout']
        return {
            'bucket_name': s3_config['BucketName'],
            'start_folder': s3_config['StartFolder'],
            'output_file': s3_config['OutputFile'],
            'columns': int(layout_config.get('Columns', 4)),
            'rows': int(layout_config.get('Rows', 6)),
            'margin': float(layout_config.get('Margin', 36)), # Points
            'header_font_size': int(layout_config.get('HeaderFontSize', 12)),
            'filename_font_size': int(layout_config.get('FilenameFontSize', 8)),
        }
    except KeyError as e:
        logging.error(f"Missing configuration key: {e}")
        raise KeyError(f"Missing configuration key in '{filename}': {e}")
    except ValueError as e:
         logging.error(f"Invalid numeric value in configuration: {e}")
         raise ValueError(f"Invalid numeric value in configuration file '{filename}': {e}")

def sanitize_filename(name):
    """Removes or replaces characters invalid for filenames."""
    # Remove leading/trailing whitespace and slashes
    name = name.strip().strip('/')
    # Replace slashes with underscores
    name = name.replace('/', '_')
    # Remove other potentially problematic characters (adjust regex as needed)
    name = re.sub(r'[\\:*?"<>|]+', '', name)
    # Replace spaces with underscores (optional)
    # name = name.replace(' ', '_')
    return name if name else "default"



def list_s3_objects_recursive(s3_client, bucket_name, prefix):
    """Recursively lists objects in an S3 prefix."""
    objects = []
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    try:
        for page in page_iterator:
            if "Contents" in page:
                for obj in page['Contents']:
                    # Ignore objects that are effectively 'folders' (size 0, end with /)
                    if obj['Size'] > 0 and not obj['Key'].endswith('/'):
                         objects.append(obj)
    except s3_client.exceptions.NoSuchBucket:
        logging.error(f"S3 Bucket '{bucket_name}' not found or access denied.")
        raise
    except Exception as e:
        logging.error(f"Error listing S3 objects: {e}")
        raise
    return objects

def get_image_from_s3(s3_client, bucket_name, object_key):
    """Downloads an image from S3 into a BytesIO object."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        image_data = response['Body'].read()
        return io.BytesIO(image_data)
    except Exception as e:
        logging.warning(f"Failed to download s3://{bucket_name}/{object_key}: {e}")
        return None

def is_jpeg(image_stream):
    """Checks if the image data in the stream is a valid JPEG."""
    try:
        img = Image.open(image_stream)
        img.verify()  # Verify closes the file, so reopen for format check
        image_stream.seek(0)
        img = Image.open(image_stream)
        is_jpeg_format = img.format in ('JPEG', 'MPO') # MPO is multi-picture JPEG
        image_stream.seek(0) # Reset stream position for later use
        return is_jpeg_format
    except UnidentifiedImageError:
        # logging.debug(f"Cannot identify image format.")
        return False
    except Exception as e:
        # logging.warning(f"Error checking image format: {e}")
        return False

def draw_page_header(c, text, page_width, page_height, margin, font_size):
    """Draws the header text at the top of the page."""
    c.setFont("Helvetica-Bold", font_size)
    header_y = page_height - margin / 2
    c.drawCentredString(page_width / 2, header_y, text)

def draw_image_and_filename(c, img_reader, filename, x, y, cell_width, cell_height, filename_font_size, text_height_allowance):
    """Draws a scaled image and its filename within a cell."""
    img_width, img_height = img_reader.getSize()
    max_img_height = cell_height - text_height_allowance

    # Calculate scaling factor to fit image within cell bounds (minus text space)
    scale_w = cell_width / img_width
    scale_h = max_img_height / img_height
    scale = min(scale_w, scale_h)

    if scale >= 1.0: # Don't scale up
        scale = 1.0

    draw_width = img_width * scale
    draw_height = img_height * scale

    # Center the image horizontally and place it at the top of the image area
    img_x = x + (cell_width - draw_width) / 2
    img_y = y + text_height_allowance + (max_img_height - draw_height) # Start drawing from bottom-left

    try:
        c.drawImage(img_reader, img_x, img_y, width=draw_width, height=draw_height, mask='auto')
    except Exception as e:
        logging.warning(f"Failed to draw image {filename}: {e}. Skipping.")
        # Optionally draw a placeholder
        c.setFont("Helvetica", filename_font_size)
        c.setFillColorRGB(0.8, 0.2, 0.2) # Reddish color for error
        c.drawCentredString(x + cell_width / 2, y + cell_height / 2, "Error drawing")
        c.setFillColorRGB(0, 0, 0) # Reset color

    # Draw filename below the image
    c.setFont("Helvetica", filename_font_size)
    text_y = y + (text_height_allowance / 2) - (filename_font_size / 2) # Center text vertically in its allowance
    c.drawCentredString(x + cell_width / 2, text_y, filename)


# --- Main Execution ---
if __name__ == "__main__":
    try:
        config = read_config()
    except (FileNotFoundError, KeyError, ValueError) as e:
        logging.critical(f"Configuration error: {e}")
        exit(1)
        
    

    BUCKET_NAME = config['bucket_name']
    START_FOLDER = config['start_folder']
    # Generate PDF filename
    pdf_filename_base = sanitize_filename(f"{START_FOLDER}")
    pdf_filename = f"contact_sheet_{pdf_filename_base}.pdf"
    OUTPUT_FILE = pdf_filename
    COLS = config['columns']
    ROWS = config['rows']
    IMAGES_PER_PAGE = COLS * ROWS
    MARGIN = config['margin']
    HEADER_FONT_SIZE = config['header_font_size']
    FILENAME_FONT_SIZE = config['filename_font_size']

    logging.info(f"Starting contact sheet generation for s3://{BUCKET_NAME}/{START_FOLDER}")
    logging.info(f"Output will be saved to: {OUTPUT_FILE}")
    logging.info(f"Layout: {COLS} columns x {ROWS} rows per page.")

    s3 = boto3.client('s3')

    # 1. List all relevant objects recursively
    logging.info("Listing objects in S3...")
    try:
        all_objects = list_s3_objects_recursive(s3, BUCKET_NAME, START_FOLDER)
    except Exception as e:
        logging.critical(f"Could not list S3 objects. Exiting. Error: {e}")
        exit(1)

    logging.info(f"Found {len(all_objects)} total objects in prefix.")

    # 2. Filter for potential JPEGs by extension and group by folder
    images_by_folder = defaultdict(list)
    for obj in all_objects:
        key = obj['Key']
        _, ext = os.path.splitext(key)
        if ext.lower() in VALID_JPEG_EXTENSIONS:
            # Group by the immediate parent directory
            folder = os.path.dirname(key)
            # Handle root folder case
            if not folder and START_FOLDER in ('', '/'):
                 folder = '/' # Represent root explicitly if needed
            elif folder == START_FOLDER.rstrip('/'): # Handle case where start folder itself has images
                 folder = START_FOLDER.rstrip('/')
            # Ensure consistent trailing slash for comparison, except for root
            if folder != '/':
                folder = folder.rstrip('/') + '/'

            images_by_folder[folder].append(key)
        else:
            logging.debug(f"Ignoring non-JPEG file by extension: {key}")

    if not images_by_folder:
        logging.warning("No JPEG images found in the specified S3 path.")
        exit(0)

    logging.info(f"Found potential JPEGs in {len(images_by_folder)} folders.")

    # 3. Create PDF
    c = canvas.Canvas(OUTPUT_FILE, pagesize=A4)
    page_width, page_height = A4

    available_width = page_width - 2 * MARGIN
    available_height = page_height - 2 * MARGIN - HEADER_FONT_SIZE * 1.5 # Extra space below header

    cell_width = available_width / COLS
    cell_height = available_height / ROWS
    text_height_allowance = FILENAME_FONT_SIZE * 2.0 # Space reserved for filename below image

    # Sort folders alphabetically for predictable output
    sorted_folders = sorted(images_by_folder.keys())

    current_image_index_on_page = 0
    first_page_for_folder = True

    for folder_path in sorted_folders:
        images_in_folder = sorted(images_by_folder[folder_path]) # Sort images within folder
        logging.info(f"Processing folder: s3://{BUCKET_NAME}/{folder_path} ({len(images_in_folder)} images)")

        # Start a new page for each new folder *unless* it's the very first image overall
        if not first_page_for_folder:
            # If previous page wasn't full, force a new page for the new folder
            if current_image_index_on_page > 0:
                 c.showPage()
                 current_image_index_on_page = 0 # Reset for new page

        # Reset page flag for this folder
        first_page_for_folder = True # Will be set to False after first page for this folder is drawn

        image_count_in_folder = 0
        for image_key in images_in_folder:
            # Check if we need a new page (start of folder or page full)
            if current_image_index_on_page == 0:
                # Don't add a page break if it's the very first image of the whole process
                if not (folder_path == sorted_folders[0] and image_count_in_folder == 0):
                     if not first_page_for_folder: # Avoid extra page break if previous was exactly full
                         c.showPage()
                header_text = f"s3://{BUCKET_NAME}/{folder_path}"
                draw_page_header(c, header_text, page_width, page_height, MARGIN, HEADER_FONT_SIZE)
                first_page_for_folder = False # Header drawn for this folder's first page

            # Download and validate image
            logging.debug(f"Processing image: {image_key}")
            image_stream = get_image_from_s3(s3, BUCKET_NAME, image_key)

            if image_stream and is_jpeg(image_stream):
                try:
                    pil_img_reader = ImageReader(image_stream) # Use ReportLab's ImageReader
                    filename = os.path.basename(image_key)

                    # Calculate position
                    col = current_image_index_on_page % COLS
                    row = ROWS - 1 - (current_image_index_on_page // COLS) # Y counts from bottom

                    # Bottom-left corner of the cell
                    cell_x = MARGIN + col * cell_width
                    cell_y = MARGIN + row * cell_height

                    # Draw the image and filename
                    draw_image_and_filename(c, pil_img_reader, filename, cell_x, cell_y, cell_width, cell_height, FILENAME_FONT_SIZE, text_height_allowance)

                    current_image_index_on_page += 1
                    image_count_in_folder += 1

                    # Check if page is full *after* drawing
                    if current_image_index_on_page >= IMAGES_PER_PAGE:
                        c.showPage()
                        current_image_index_on_page = 0 # Reset for next page
                        # If we are still in the same folder, draw the header again
                        if image_count_in_folder < len(images_in_folder):
                             header_text = f"s3://{BUCKET_NAME}/{folder_path}"
                             draw_page_header(c, header_text, page_width, page_height, MARGIN, HEADER_FONT_SIZE)

                except Exception as e:
                    logging.error(f"Error processing or drawing image {image_key}: {e}")
                    # Move to next potential spot if an error occurred during drawing?
                    # Decide if an error should skip a grid slot or just log and continue
            else:
                if image_stream:
                     logging.warning(f"Skipping non-JPEG file (verified): {image_key}")
                # else: download failed, already logged in get_image_from_s3

        # End of folder processing - important: set page index to 0 if we finished mid-page
        # to force a new page for the *next* folder (unless it was already 0).
        if current_image_index_on_page > 0:
             # Don't add showPage here, let the start of the next folder handle it
             pass # The next folder loop iteration will call showPage if needed


    # 4. Save the PDF
    try:
        c.save()
        logging.info(f"Successfully created contact sheet: {OUTPUT_FILE}")
    except Exception as e:
        logging.error(f"Failed to save PDF file '{OUTPUT_FILE}': {e}")
        