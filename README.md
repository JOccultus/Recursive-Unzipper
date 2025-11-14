49 66 20 69 74 20 77 6f 72 6b 73 2c 20 4a 6f 65 20 70 72 6f 62 61 62 6c 79 20 77 72 6f 74 65 20 69 74 2e 20 49 66 20 69 74 20 64 6f 65 73 6e 27 74 20 77 6f 72 6b 2c 20 4a 6f 65 20 64 65 66 69 6e 69 74 65 6c 79 20 77 72 6f 74 65 20 69 74 2e

# Recursive-Unzipper
Program to unzip ZIP archives that contain other ZIP archives, all in one go.

## How This Works:
1.	Begins loop.
2.	Launches simple GUI window with a button, progress bar, and status label. Clicking the button pulls up native file selector.
3.	File dialog allows user to select single ZIP archive.
4.	Opens selected ZIP archive and recursively scans to count files needed to be extracted.
5.	Resets progress counters, and sets progress bar max to number of files found.
6.	Runs extraction in background thread.
7.	Recursively extracts files from main ZIP and nested ZIPs, flattening directories and creating directories as needed.
8.	Handles file name collisions by appending a number after the file name.
9.	Pretty-prints JSON files.
10.	Creates extraction map recording original file -> extracted file path mappings.
11.	Updates GUI utilizing thread-safe queue.

## Important Notes:
1.  It recursively searches through a ZIP archives subdirectories to unzip all files within a directory.
2.  It flattens the zip archive.
3.  It handles long paths too, if they're not already enabled on Windows.
4.  The label doesn't update constantly, but the progress bar does, so please be patient; nothing is wrong, the program is still working.
5.  Sometimes it takes a while to scan the ZIP archive, so please be patient; nothing is wrong, the program is still working.
