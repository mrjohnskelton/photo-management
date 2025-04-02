import os
import piexif
import datetime

def rename_images_by_exif_date(target_directory, source_directory, output_filename="rename_commands.sh"):
    """
    Renames JPEG images in a source directory and its subdirectories based on EXIF date/time,
    moving all renamed files to the target directory.

    Args:
        target_directory (str): The directory where renamed files will be moved.
        source_directory (str): The directory containing the images to be renamed.
        output_filename (str): The name of the output script file.
    """

    rename_commands = []
    file_counters = {}  # Dictionary to track file name counters

    files_to_process = []
    for root, _, files in os.walk(source_directory):
        for filename in files:
            if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
                files_to_process.append(os.path.join(root, filename))

    for filepath in files_to_process:
        try:
            exif_dict = piexif.load(filepath)
            if piexif.ImageIFD.DateTime in exif_dict["0th"]:
                date_time_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode("utf-8")
                date_time_obj = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
                new_filename_base = date_time_obj.strftime("%Y-%m-%d-%H-%M")
            elif piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                date_time_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode("utf-8")
                date_time_obj = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
                new_filename_base = date_time_obj.strftime("%Y-%m-%d-%H-%M")
            elif piexif.ExifIFD.DateTimeDigitized in exif_dict["Exif"]:
                date_time_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized].decode("utf-8")
                date_time_obj = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
                new_filename_base = date_time_obj.strftime("%Y-%m-%d-%H-%M")
            else:
                print(f"Warning: No EXIF date/time found for {filepath}. Skipping.")
                continue
        except (piexif.InvalidImageDataError, KeyError, ValueError) as e:
            print(f"Warning: Error processing {filepath}: {e}. Skipping.")
            continue

        new_filename_counter = file_counters.get(new_filename_base, 0)
        new_filename = f"{new_filename_base}-{new_filename_counter:02d}.JPG"
        new_filepath = os.path.join(target_directory, new_filename)

        while os.path.exists(new_filepath):
            new_filename_counter += 1
            new_filename = f"{new_filename_base}-{new_filename_counter:02d}.JPG"
            new_filepath = os.path.join(target_directory, new_filename)

        file_counters[new_filename_base] = new_filename_counter + 1

        rename_commands.append(f'mv "{filepath}" "{new_filepath}"')

    with open(output_filename, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("set -e\n")
        f.write("set -u\n")
        f.write("set -o pipefail\n")
        f.write("set -o noclobber\n")
        f.write('\n'.join(rename_commands))

    print(f"Rename commands written to {output_filename}")

if __name__ == "__main__":
    target_dir = "/Users/john_skelton/Documents/202503 - India"  # Replace with the target directory
    source_dir = "/Users/john_skelton/Documents/202503 - India/Johns Phone"  # Replace with the source directory

    if not os.path.exists(target_dir):
        os.makedirs(target_dir) #create target dir if not exists

    rename_images_by_exif_date(target_dir, source_dir)