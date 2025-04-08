import os
import io
import boto3
import exifread
import configparser
import logging
from pathlib import Path
import re # For sanitizing filename
from typing import List, Dict, Tuple

# exif_getter.py

from PIL import Image
from PIL.ExifTags import TAGS

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
            path,name=obj['Key'].rsplit('/',1)
            files[name] = obj['Key'] #Fragile as duplicate filenames will get overwritten - but so long as I've got it once risk is minimal?
    return files

def get_local_files(directory: str) -> Dict[str, str]:
    files = {}
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files[filename] = file_path
    return files


def compare_files(s3_files: Dict[str, str], local_files: Dict[str, str], bucket_name: str) -> Tuple[List[str], List[str], List[str]]:
    s3_only = {}
    local_only = {}
    common_names = {}

    s3_names = set(s3_files.keys())
    local_names = set(local_files.keys())
    
    # Files with commmon names regardles of path
    common_name_keys = s3_names.intersection(local_names)
    for key in common_name_keys:
        common_names[key] = s3_files[key] + " <--> " + local_files[key]
        
    local_only_keys = local_names.difference(s3_names)
    for key in local_only_keys:
        local_only[key] = local_files[key] + " not matched in S3"
        
    s3_only_keys = s3_names.difference(local_names)
    for key in s3_only_keys:
        s3_only[key] = s3_files[key] + " not matched locally"
    
    return common_names, s3_only, local_only

def list_results(heading:str, dct:Dict[str,str], of):
    print("\n\n\n"+heading, file=of)
    keys = dct.keys()
    for key in keys:
        print(f"{key}:\t{dct[key]}", file=of)

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

    common_names, s3_only, local_only = compare_files(s3_files, local_files, BUCKET_NAME)
    
    with open("Compare "+sanitize_filename(START_FOLDER)+".txt", "w") as f:
        list_results(f"Files with common names ({len(common_names)}):", common_names, f)
        list_results(f"Files in S3 but not in local ({len(s3_only)}):", s3_only, f)
        list_results(f"Files in local but not in S3 ({len(local_only)}):", local_only, f)

if __name__ == "__main__":
    main()