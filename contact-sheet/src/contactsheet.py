import boto3
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import math

def create_contact_sheet(bucket_name, folder_path):
    s3 = boto3.client('s3')
    
    # Setup page dimensions (A4 at 300 dpi)
    page_width, page_height = 2480, 3508
    columns, rows = 4, 6
    margin = 50
    image_width = (page_width - (columns + 1) * margin) // columns
    image_height = (page_height - (rows + 1) * margin) // rows

    # Initiate a new contact sheet
    contact_sheet = Image.new('RGB', (page_width, page_height), 'white')
    draw = ImageDraw.Draw(contact_sheet)

    # Define font for the filename text
    try:
        font = ImageFont.truetype("arial", 20)
    except IOError:
        font = ImageFont.load_default()

    # Get the JPG files from the specified folder in the bucket
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)
    images = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith(('.jpg', '.jpeg'))]
    
    x, y = margin, margin
    for i, img_key in enumerate(images):
        # Download the image
        obj = s3.get_object(Bucket=bucket_name, Key=img_key)
        img_data = obj['Body'].read()
        image = Image.open(BytesIO(img_data))
        
        # Scale the image
        image.thumbnail((image_width, image_height))
        
        # Paste the image into the sheet
        contact_sheet.paste(image, (x, y))
        
        # Draw the filename
        draw.text((x, y + image_height), img_key.split('/')[-1], font=font, fill='black')
        
        # Update the x-coordinate
        x += image_width + margin
        if (i + 1) % columns == 0:
            x = margin
            y += image_height + font.getbbox(img_key.split('/')[-1])[1] + margin
        
        # Check if we filled the page
        if (i + 1) % (columns * rows) == 0 or i == len(images) - 1:
            # Save or show the contact sheet
            contact_sheet.show()
            contact_sheet.save(f"contact_sheet_{math.ceil((i + 1) / (columns * rows))}.jpg")
            # Start a new contact sheet for next batch
            contact_sheet = Image.new('RGB', (page_width, page_height), 'white')
            draw = ImageDraw.Draw(contact_sheet)
            x, y = margin, margin

if __name__ == "__main__":
    bucket_name = 'mrjohnskelton-personal-photos'
    folder_path = '2002/'
    create_contact_sheet(bucket_name, folder_path)

exit()

##########
# 
import boto3
from botocore.config import Config
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

def generate_contact_sheet(bucket_name, folder_key):
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_key)
    
    images = []
    for obj in response['Contents']:
        if obj['Key'].lower().endswith(('jpg', 'jpeg')):
            images.append(obj['Key'])
    
    if not images:
        return "No JPEG images found in the specified folder."
    
    width, height = A4
    img_width = width / 4
    img_height = height / 6
    c = canvas.Canvas(f"{folder_key.strip('/')}_contact_sheet.pdf", pagesize=A4)
    
    x = 0
    y = height
    for idx, img_key in enumerate(images):
        img_obj = s3_client.get_object(Bucket=bucket_name, Key=img_key)
        # 
        print(img_obj)
        img = Image.open(BytesIO(img_obj['Body'].read()))
        img.thumbnail((img_width, img_height), Image.LANCZOS)
        
        if idx % 24 == 0 and idx != 0:
            c.showPage()
            x = 0
            y = height
        
        y -= img_height
        c.drawImage(BytesIO(img.tobytes()), x, y, width=img_width, height=img_height)
        c.drawString(x, y - 10, img_key.split('/')[-1])  # Draw the filename underneath the image
        
        x += img_width
        if x >= width:
            x = 0
            y -= img_height
            
        if (idx + 1) % 24 == 0:
            y = height
    
    c.save()
    return f"Contact sheet created for folder {folder_key}"

bucket_name = 'mrjohnskelton-personal-photos'
folder_key = '2002/'
result = generate_contact_sheet(bucket_name, folder_key)
print(result)