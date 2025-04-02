# Contact Sheet

## GenAI Prompt

I have photographs stored in folders in an AWS S3 bucket.  I need to write a python programme which can iterate through the photographs in a folder and produce a contact sheet of the images.  The photographs will have a filetype of "jpg", "JPG", or "jpeg'.  Other filetypes which are also JPEG images should also be processed. Anything that is not a JPEG file should be ignored.  Each contact sheet should be A4 sized paper.  Each sheet should show 4 columns and 6 rows of scaled down  photograph images with the filename of the photograph underneath the scaled down image.  Write a python program that will do this.

## Output

Here's a breakdown of what the script does:

Configuration: Set up the boto3 client for AWS S3 and fetch JPEG images from the specified bucket/folder.

Processing Images: For each image, it converts to a thumbnail that fits the card size for an A4 format, with 4 columns and 6 rows.

PDF Creation: Use reportlab to create a PDF document for the contact sheet. Each page of the PDF will have a grid of thumbnails.

Save and Output: Finally, the script saves the PDF file and prints a message indicating successful creation.
Notes:

Make sure to configure your AWS credentials for boto3 to access the S3 bucket.

Adjust the bucket_name and folder_key variables according to your specific use case.

The script checks file names to include only JPEG files (with a simple extension check for jpg and jpeg).
