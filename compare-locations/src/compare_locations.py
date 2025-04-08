import os
import boto3
import exifread
from typing import List, Dict, Tuple

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

def compare_files(s3_files: Dict[str, str], local_files: Dict[str, str]) -> Tuple[List[str], List[str]]:
    s3_only = []
    local_only = []

    s3_names = set(s3_files.keys())
    local_names = set(local_files.keys())

    common_names = s3_names & local_names

    for name in common_names:
        s3_file = s3_files[name]
        local_file = local_files[name]
        s3_exif = get_exif_data(s3_file)
        local_exif = get_exif_data(local_file)
        if s3_exif != local_exif:
            s3_only.append(s3_file)
            local_only.append(local_file)

    s3_only.extend([s3_files[name] for name in s3_names - common_names])
    local_only.extend([local_files[name] for name in local_names - common_names])

    return s3_only, local_only

def main():
    bucket_name = 'your-s3-bucket'
    s3_prefix = 'your/s3/prefix'
    local_directory = 'your/local/directory'

    s3_files = get_s3_files(bucket_name, s3_prefix)
    local_files = get_local_files(local_directory)

    s3_only, local_only = compare_files(s3_files, local_files)

    print("Files in S3 but not in local:")
    for file in s3_only:
        print(file)

    print("\nFiles in local but not in S3:")
    for file in local_only:
        print(file)

if __name__ == "__main__":
    main()