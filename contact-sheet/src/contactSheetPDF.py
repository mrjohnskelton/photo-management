import boto3
import os
from PIL import Image
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import A4

def create_contact_sheet(bucket_name, folder_prefix):
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)

    # A4 size dimensions and layout
    page_width, page_height = A4
    images_per_row, rows_per_page = 4, 6
    image_width = page_width / images_per_row
    image_height = page_height / rows_per_page

    file_path = f"{folder_prefix.strip('/')}.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)

    row_count = 0
    col_count = 0

    for page in page_iterator:
        if "Contents" in page:
            for obj in page['Contents']:
                file_key = obj['Key']
                if file_key.lower().endswith(('jpg', 'jpeg')):
                    obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
                    img_data = obj['Body'].read()
                    
                    img = Image.open(BytesIO(img_data))
                    img.thumbnail((image_width, image_height))
                    
                    x_position = col_count * image_width
                    y_position = page_height - ((row_count + 1) * image_height)
                    
                    # Draw image to PDF
                    c.drawInlineImage(img, x_position, y_position, width=image_width, height=image_height)
                    
                    # Adding the filename
                    c.drawString(x_position, y_position - 10, os.path.basename(file_key))

                    # Update positions for the next image
                    col_count += 1
                    if col_count >= images_per_row:
                        col_count = 0
                        row_count += 1

                    # Check if a new PDF page is needed
                    if row_count >= rows_per_page:
                        c.showPage()
                        col_count, row_count = 0, 0

    # Save the PDF file
    c.save()
    print(f"Contact sheet created and saved as {file_path}")

# Usage
bucket_name = 'mrjohnskelton-personal-photos'
folder_path = '2002/'
create_contact_sheet(bucket_name, folder_path)