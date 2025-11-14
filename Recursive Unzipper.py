# 49 66 20 69 74 20 77 6f 72 6b 73 2c 20 4a 6f 65 20 70 72 6f 62 61 62 6c 79 20 77 72 6f 74 65 20 69 74 2e 20 49 66 20 69 74 20 64 6f 65 73 6e 27 74 20 77 6f 72 6b 2c 20 4a 6f 65 20 64 65 66 69 6e 69 74 65 6c 79 20 77 72 6f 74 65 20 69 74 2e

# RECURSIVE UNZIPPER

# imports
import io # for opening nested ZIP bytes as files
import json # for creating extraction map
import os # for system controls
import shutil # for file manipulation
import zipfile # for manipulating ZIP archives
import threading # for assigning threads
import queue # thread-safe queue for progress tracking
from pathlib import Path, PurePosixPath # for path manipulation
# for GUI
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

CHUNK = 64 * 1024 # size of streaming chunk for copying file data

class ZipExtractorApp: # GUI
    def __init__(self, root):
        """
        Constructor.
        """
        self.root = root # instance variable
        root.title("Recursive ZIP Extractor") # name title bar
        self.progress_q = queue.Queue() # thread-safe queue to communicate progress update
        # counters
        self.total_files = 0 # variable to hold how many files to be extracted
        self.extracted_count = 0 # variable to hold how many files have been extracted so far

        # UI elements of main window
        frm = ttk.Frame(root, padding=12) # container for other widgets
        frm.grid(sticky="nsew") # place frame in window and expand in all directions
        ttk.Button(frm, text="Select ZIP to Extract", command=self.select_zip).grid(row=0, column=0, pady=(0,10)) # design button to call select_zip button
        self.progress = tk.IntVar(value=0) # value to bind progress bar variable to
        self.pbar = ttk.Progressbar(frm, orient="horizontal", length=500, mode="determinate", maximum=1, variable=self.progress) # normalize progress, show definite progress, link to variable
        self.pbar.grid(row=1, column=0, sticky="we") # place progress bar in second row of grid
        self.status = ttk.Label(frm, text="No archive selected") # label to show status messages to user with initial message
        self.status.grid(row=2, column=0, sticky="w", pady=(6,0)) # place label in third row of grid

    def select_zip(self):
        """
        Allow user to select ZIP archive through native file explorer. Triggered when user clicks button. Opens file dialog.
        """
        path_str = filedialog.askopenfilename(title="Choose a ZIP file", filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]) # native file picker, returns file path as string
        # abort when user cancels
        if not path_str:
            return # early exit
        zip_path = Path(path_str) # convert string filepath to Path
        dest_root = zip_path.parent / f"Extracted - {zip_path.stem}" # create sibling folder
        dest_root.mkdir(exist_ok=True) # avoid overwrite

        try: # attempt tp open ZIP
            with zipfile.ZipFile(zip_path, 'r') as zf: # open in read mode
                self.total_files = scan_zip(zf) # call method to count how many files need to be extracted
        except zipfile.BadZipFile: # if not valid ZIP
            messagebox.showerror("Invalid ZIP", "The selected file is not a valid ZIP archive.") # shows error dialog
            return # exit
        if self.total_files == 0: # if no ZIP found
            messagebox.showinfo("Nothing to extract", "No regular files found to extract.") # shows info dialog
            return # exit

        # resets progress tracking
        self.progress.set(0)
        self.extracted_count = 0
        self.pbar.config(maximum=self.total_files) # set progress bar maximum to total number of files
        self.status.config(text=f"Preparing to extract {self.total_files} files...") # update status label

        # keep GUI responsive during extraction
        worker = threading.Thread(target=self.worker_extract, args=(zip_path, dest_root), daemon=True) # spawn background thread
        worker.start()
        self.root.after(100, self.poll_queue) # call poll_queue method after 100 ms

    def worker_extract(self, zip_path: Path, dest_root: Path):
        """
        Creates background thread for extraction.

        Arguments:
            zip_path {Path} -- filepath of main ZIP archive
            dest_root {Path} -- path of extracted folder
        """
        mapping = {} # dictionary to hold mapping of original to extracted path mappings
        # extract files
        with zipfile.ZipFile(zip_path, 'r') as zf: # open zipfile in read mode
            extract_zip(zf, dest_root, Path(), self.progress_q, mapping) # call extract_zip function, pass destination location, queue to send updates, and dictionary to catch map of locations
        # write mapping to JSON next to extracted files
        try:
            map_file = dest_root / "Extraction_Map.json"
            with open(map_file, "w", encoding="utf-8") as mf:
                json.dump(mapping, mf, indent=2, ensure_ascii=False)
        except Exception:
           pass # silently ignore
        self.progress_q.put("DONE") # signal GUI thread that extraction and map write are finished

    def poll_queue(self):
        """
        Updates the progress bar.
        """
        updated = False # flag to track whether any progress was made in polling cycle to determine whether to refresh status label
        while not self.progress_q.empty(): # run while queue is not empty
            item = self.progress_q.get() # read queued item
            # update UI that queue is finished
            if item == "DONE":
                self.status.config(text=f"Finished extracting {self.total_files} files") # update label
                self.progress.set(self.total_files) # set progress bar to full
                messagebox.showinfo("Extraction Complete", f"All {self.total_files} files extracted to 'Extracted'.\nMapping saved to extraction_map.json.") # pop up message box with success message.
            # advance progress bar
            else:
                self.extracted_count += int(item) # increments counter
                self.progress.set(self.extracted_count) # update progress bar
                updated = True # indicate that progress was made
        if not updated:
            self.status.config(text=f"Extracted {self.extracted_count} / {self.total_files} files") # refresh status label to show current progress if no progress was made in this cycle
        self.root.after(100, self.poll_queue) # reschedules poll_queue to run after 100 ms

def scan_zip(zf: zipfile.ZipFile) -> int:
    """
    Helper function; count extractable regular files inside of ZIP archive including files inside nested ZIPs.

    Arguments:
        zf {ZipFile} -- main ZIP archive

    Returns:
        total {int} -- total number of regular files found across entire archive including nested archives
    """
    total = 0 # variable to track number of zip files found
    for info in zf.infolist(): # loop through every entry in ZIP archive
        name = info.filename # store path as POSIX string (forward slashes)
        if name.endswith('/'): # if directory
            continue # skip
        if name.lower().endswith('.zip'): # if ZIP file
            data = zf.read(name) # read bytes
            with zipfile.ZipFile(io.BytesIO(data)) as nested: # wrap bytes in BytesIO stream to simulate file-like object
                total += scan_zip(nested) # recursively call scan_zip to count contents
        else:
            total += 1 # increment count for regular file
    return total # return number of regular files across entire nesting scheme

def make_unique_path(path: Path) -> Path:
    """
    Helper function; returns path or a new Path with ' (n)' appended before full suffixes if exists to avoid overwriting on collision.

    Arguments:
        path {Path} -- current path candidate.

    Returns:
        candidate {Path} -- final path candidate.
    """
    # return original path immediately if safe
    if not path.exists():
        return path
    parent = path.parent # parent directory containing file
    name = path.name # full filename including suffixes
    suffixes = ''.join(path.suffixes) # concatenates all suffixes
    stem = name[:-len(suffixes)] if suffixes else name # extracts base name by stripping suffixes and handles multi-suffix cases properly too
    i = 1 # counter value
    # determine name if collision
    while True:
        candidate = parent / f"{stem} ({i}){suffixes}" # construct new candidate path
        # return candidate if no collision
        if not candidate.exists():
            return candidate
        i += 1 # iterate counter value otherwise

def to_windows_long_path(p: Path | str):
    """
    Helper function; returns windows long path if possible.

    Arguments:
        p {Path | str} -- path or windows long path

    Returns:
        {str} -- windows long path
    """
    s = str(p) # convert path to plain Python string
    # return original if not Windows
    if os.name != "nt":
        return s
    s = os.path.abspath(s) # convert string to absolute path
    # return unchanged path if already long-path prefixed
    if s.startswith("\\\\?\\"):
        return s
    # prefix for network paths
    if s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + s.lstrip("\\").replace("/", "\\") # \\server\share -> \\?\UNC\server\share
    # prefix and return
    return "\\\\?\\" + s.replace("/", "\\") # C:\some\path -> \\?\C:\some\path

def read_json_from_zip(zf: zipfile.ZipFile, member_name: str, encoding: str = 'utf-8'):
    """
    Helper function; reads JSON file from ZIP archive.

    Arguments:
         zf {zipfile.ZipFile} -- main ZIP archive
         member_name {str} -- member of ZIP archive
         encoding {str} -- encoding of JSON file

    Returns:
        {dict} -- dictionary with JSON file contents
    """
    with zf.open(member_name) as binf: # opens specified file inside ZIP archive as binary stream
        with io.TextIOWrapper(binf, encoding=encoding) as txtf: # wraps binary stream with TextIOWrapper to decode bytes into text
            return json.load(txtf) # read text stream and parse as Python dictionary into JSON

def extract_zip(zf, dest_root, rel_root, progress_q, mapping):
    """
    Core function; extracts the ZIP files.

    Arguments:
        zf {ZipFile} -- open Zip archive
        dest_root {Path} -- location for files to be extracted to
        rel_root {PurePosixPath} -- relative path prefix for mapping and nesting
        progress_q {queue} -- signal progress to GUI
        mapping {dict} -- holds mapping of original files to extracted files
    """
    for info in zf.infolist(): # loop through each entry in the ZIP
        name = info.filename # get member path as POSIX

        # for subdirectories
        if name.endswith('/'):
            target_dir = dest_root.joinpath(*PurePosixPath(name).parts) # convert POSIX into Path
            os.makedirs(to_windows_long_path(target_dir), exist_ok=True) # calls long path helper function to create directory
            continue # skip further processing

        parts = PurePosixPath(name).parts # break string into Path components
        member_rel = rel_root.joinpath(*parts) # combine parts with relative root for mapping

        try:
            target_path = (dest_root / member_rel).resolve() # produce resolved absolute path
        # fallback to non-resolved path
        except Exception:
            target_path = dest_root / member_rel
        # ensure extraction stays under dest_root
        if not str(target_path).startswith(str(dest_root.resolve())): # ensure resolved path safety
            continue # skips entry trying to escape extraction root

        # handle nested ZIP files
        if name.lower().endswith('.zip'):
            data = zf.read(name) # read as bytes
            parent_rel = rel_root.joinpath(*PurePosixPath(name).parent.parts) # place extracted nested contents next to nested archive location
            with zipfile.ZipFile(io.BytesIO(data)) as nested: # open ZIP from bytes buffer
                extract_zip(nested, dest_root, parent_rel, progress_q, mapping) # recursive call
            continue

        # ensure destination dir exists and get unique filename on collision
        os.makedirs(to_windows_long_path((dest_root / member_rel).parent), exist_ok=True) # make directory if it doesn't exist
        unique_target = make_unique_path(dest_root / member_rel) # call helper function to make unique path

        # JSON handling pretty-write
        if name.lower().endswith('.json'):
            try:
                with zf.open(name) as binf, io.TextIOWrapper(binf, encoding="utf-8") as txtf: # open binary stream and wrap using TextIOWrapper
                    obj = json.load(txtf) # parse JSON file
                with open(to_windows_long_path(unique_target), "w", encoding="utf-8") as out:
                    json.dump(obj, out, ensure_ascii=False, indent=2)
            # fallback to raw binary
            except Exception:
                # write bytes without interpretation
                with zf.open(name) as src, open(to_windows_long_path(unique_target), "wb") as dst:
                    for chunk in iter(lambda: src.read(CHUNK), b""):
                        dst.write(chunk)
        # non-JSON regular files
        else:
            with zf.open(name) as src, open(to_windows_long_path(unique_target), "wb") as dst:
                for chunk in iter(lambda: src.read(CHUNK), b""): # read block until empty bytes
                    dst.write(chunk)

        original_posix = member_rel.as_posix() # convert relative path into POSIX
        mapping[original_posix] = str(unique_target.resolve()) # records resolved path
        progress_q.put(1) # update progress bar

def main():
    """
    Main function to run logic; for modularization purposes.
    """
    root = tk.Tk()
    app = ZipExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()