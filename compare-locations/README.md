# Compare Locations

Compare the contents of a local folder/mount and S3 to chek I've got the same files in both locations.

## Prompt

I need to compare the content of two folders.  One of the folders is on AWS S3 - let's call this location A. The other folder will be local or a local mount - let's call this location B.  I want to tree walk all the sub-folders of location A and location B to look for matching files or files which are in one of the locations but not the other.  The definition of a matching file could be that either (1) they have the same name or (2) they have the same EXIF data even though the names are different.  The folder structures of each location should be ignored for matching purposes, it's only the files themselves I need to compare.  The output of the comparison should list all of the files that are in location A but not location B, then all the files that are in location B but not in location A.  For each entry in the output lists the folder or sub-folder locations of the files shoud be included in the output.  Write a python program that achieves this.