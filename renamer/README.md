# Renamer 

## Explanation:

### Import Libraries:

- os: For file and directory operations.
- piexif: For reading EXIF metadata from JPEG images.
- datetime: For working with dates and times.

### rename_images_by_exif_date(directory, output_filename) Function:

Takes the directory and output filename as input.

Initializes an empty list rename_commands to store the mv commands.

Initializes an empty dictionary file_counters to track file name counters.

Uses os.walk() to recursively traverse the directory and its subdirectories.

For each file, it checks if it's a JPEG image.

It attempts to extract the date and time from the EXIF metadata using piexif.load(). It checks for the presence of piexif.ImageIFD.DateTime, piexif.ExifIFD.DateTimeOriginal, and piexif.ExifIFD.DateTimeDigitized, in that order. This helps to handle images from different camera sources.

If EXIF data is found, it formats the new filename using datetime.datetime.strftime() in the "YYYY-MM-DD-HH-mm" format.

It checks for filename clashes and appends a "-0X" suffix to ensure uniqueness.

It appends the mv command to the rename_commands list.

It handles potential piexif errors and prints warnings for files that can't be processed.

It writes the mv commands to the output script file.

Writes the bash header lines to the script file.

Prints a message indicating that the commands have been written.

### if __name__ == "__main__": Block:

Sets the directory_to_process variable to the directory containing your images.

Calls the rename_images_by_exif_date() function to process the images.


## How to Use:

Install piexif:

Bash

pip install piexif

Replace "images":

- In the if __name__ == "__main__": block, replace "images" with the path to the directory containing your JPEG images.

Run the Python Script:

Bash

- `python your_script_name.py`

Execute the rename_commands.sh Script:

- This will create a file named rename_commands.sh in the same directory as the Python script.
- Make the script executable: chmod +x rename_commands.sh
- Run the script: ./rename_commands.sh
- This will rename your JPEG images based on their EXIF date and time, with unique sfilenames to prevent clashes.
