import os
import boto3
import exifread
import configparser
import logging
from pathlib import Path
import re # For sanitizing filename
from typing import List, Dict, Tuple

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'config.ini'

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
        return {
            'bucket_name': s3_config['BucketName'],
            'start_folder': s3_config['StartFolder'],
            'local_folder': s3_config['LocalFolder']
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



def get_s3_files(bucket_name: str, prefix: str) -> Dict[str, str]:
    s3 = boto3.client('s3')
    files = {}
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            files[obj['Key']] = obj['Key']
    return files

def get_local_files(directory: str) -> Dict[str, str]:
    files = {}
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files[filename] = file_path
    return files

def get_exif_data(file_path: str) -> Dict:
    with open(file_path, 'rb') as f:
        tags = exifread.process_file(f)
    return tags

def compare_files(s3_files: Dict[str, str], local_files: Dict[str, str]) -> Tuple[List[str], List[str], List[str], List[str]]:
    s3_only = []
    local_only = []
    common_names = []
    identical_exif = []

    s3_names = set(s3_files.keys())
    local_names = set(local_files.keys())

    # Compare files with common names
    for name in s3_names & local_names:
        print(".", end="")
        s3_file = s3_files[name]
        local_file = local_files[name]
        s3_exif = get_exif_data(s3_file)
        local_exif = get_exif_data(local_file)
        if s3_exif == local_exif:
            common_names.append((s3_file, local_file))
        else:
            s3_only.append(s3_file)
            local_only.append(local_file)

    # Compare files with different names based on EXIF data
    for s3_name, s3_file in s3_files.items():
        print(".", end="")
        if s3_name not in local_names:
            s3_exif = get_exif_data(s3_file)
            found = False
            for local_name, local_file in local_files.items():
                if local_name not in s3_names:
                    local_exif = get_exif_data(local_file)
                    if s3_exif == local_exif:
                        identical_exif.append((s3_file, local_file))
                        found = True
                        break
            if not found:
                s3_only.append(s3_file)

    for local_name, local_file in local_files.items():
        if local_name not in s3_names and not any(local_file in pair for pair in identical_exif):
            local_only.append(local_file)

    return common_names, identical_exif, s3_only, local_only

def main():
    try:
        config = read_config()
    except (FileNotFoundError, KeyError, ValueError) as e:
        logging.critical(f"Configuration error: {e}")
        exit(1)
        
    

    BUCKET_NAME = config['bucket_name']
    START_FOLDER = config['start_folder']
    LOCAL_FOLDER = config['local_folder']

    s3_files = get_s3_files(BUCKET_NAME, START_FOLDER)
    local_files = get_local_files(LOCAL_FOLDER)

    print("Starting comparison", end="")
    common_names, identical_exif, s3_only, local_only = compare_files(s3_files, local_files)

    print("Files with common names and identical EXIF data:")
    for s3_file, local_file in common_names:
        print(f"S3: {s3_file} <-> Local: {local_file}")

    print("\nFiles with identical EXIF data but different names:")
    for s3_file, local_file in identical_exif:
        print(f"S3: {s3_file} <-> Local: {local_file}")

    print("\nFiles in S3 but not in local:")
    for file in s3_only:
        print(file)

    print("\nFiles in local but not in S3:")
    for file in local_only:
        print(file)

if __name__ == "__main__":
    main()