import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import shutil
import requests # For downloading FFmpeg: pip install requests
import zipfile # For extracting FFmpeg
import platform # To check OS
import webbrowser # For opening links

APP_NAME = "YouTube Downloader by AboulNasr"
APP_AUTHOR_IG = "https://www.instagram.com/mahmoud.aboulnasr/"
FFMPEG_DOWNLOAD_URL_WINDOWS = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# --- Color Scheme ---
COLOR_BACKGROUND = "#2E2E2E"  # Dark Gray
COLOR_FRAME_BG = "#3C3C3C"    # Lighter Dark Gray for frames
COLOR_TEXT = "#E0E0E0"        # Light Gray for text
COLOR_BUTTON = "#4A4A4A"      # Medium Gray for buttons
COLOR_BUTTON_ACCENT = "#0078D7" # Blue Accent (like before)
COLOR_BUTTON_CANCEL = "#D32F2F" # Red for Cancel
COLOR_PROGRESS_BAR = "#0078D7" # Blue for progress bar
COLOR_LINK = "#64B5F6"        # Light Blue for links

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("720x650") # Adjusted size
        self.root.configure(bg=COLOR_BACKGROUND)
        self.root.resizable(False, False)

        self.ffmpeg_path = None
        self.ffmpeg_download_in_progress = False
        self.download_thread = None
        self.cancel_download_event = threading.Event() # For interrupting download

        # --- Styling ---
        self.style = ttk.Style()
        # Attempt to use a theme that might respect background colors better
        available_themes = self.style.theme_names()
        if 'clam' in available_themes:
            self.style.theme_use('clam')
        elif 'alt' in available_themes:
            self.style.theme_use('alt')
        # Else, it will use the default, which might not fully adopt all custom colors for all widgets

        # General widget styling
        self.style.configure(".", background=COLOR_FRAME_BG, foreground=COLOR_TEXT, fieldbackground=COLOR_BUTTON, borderwidth=1)
        self.style.map(".", background=[('active', COLOR_BUTTON_ACCENT)], foreground=[('active', COLOR_TEXT)])

        self.style.configure("TFrame", background=COLOR_BACKGROUND)
        self.style.configure("TLabelframe", background=COLOR_BACKGROUND, foreground=COLOR_TEXT, bordercolor=COLOR_TEXT)
        self.style.configure("TLabelframe.Label", background=COLOR_BACKGROUND, foreground=COLOR_TEXT, font=("Helvetica", 11, "bold"))
        
        self.style.configure("TButton", padding=8, font=("Helvetica", 10), background=COLOR_BUTTON, foreground=COLOR_TEXT)
        self.style.map("TButton", background=[('active', COLOR_BUTTON_ACCENT), ('disabled', COLOR_BUTTON)])
        
        self.style.configure("Accent.TButton", background=COLOR_BUTTON_ACCENT, foreground="white")
        self.style.map("Accent.TButton", background=[('active', '#005A9E')]) # Darker blue on active
        
        self.style.configure("Cancel.TButton", background=COLOR_BUTTON_CANCEL, foreground="white")
        self.style.map("Cancel.TButton", background=[('active', '#A30000')]) # Darker red on active
        
        self.style.configure("TLabel", font=("Helvetica", 11), background=COLOR_BACKGROUND, foreground=COLOR_TEXT)
        self.style.configure("Bold.TLabel", font=("Helvetica", 11, "bold"), background=COLOR_BACKGROUND, foreground=COLOR_TEXT)
        self.style.configure("Small.TLabel", font=("Helvetica", 9), background=COLOR_BACKGROUND, foreground=COLOR_TEXT)
        self.style.configure("Link.TLabel", font=("Helvetica", 9, "underline"), foreground=COLOR_LINK, background=COLOR_BACKGROUND, cursor="hand2")
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background=COLOR_BACKGROUND, foreground=COLOR_TEXT)

        self.style.configure("TCombobox", font=("Helvetica", 10), padding=5)
        self.style.map('TCombobox', fieldbackground=[('readonly', COLOR_BUTTON)], foreground=[('readonly', COLOR_TEXT)])
        
        self.style.configure("TEntry", font=("Helvetica", 10), padding=5, fieldbackground=COLOR_BUTTON, foreground=COLOR_TEXT)
        
        self.style.configure("Horizontal.TProgressbar", troughcolor=COLOR_BUTTON, background=COLOR_PROGRESS_BAR, thickness=20)


        # --- Main Frame ---
        self.main_frame = ttk.Frame(self.root, padding="20 20 20 20", style="TFrame")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Title and Credits ---
        title_label = ttk.Label(self.main_frame, text=APP_NAME, style="Header.TLabel")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0,15), sticky=tk.W)
        
        credits_frame = ttk.Frame(self.main_frame, style="TFrame")
        credits_frame.grid(row=0, column=1, columnspan=2, sticky=tk.E, pady=(0,15)) # Adjusted columnspan
        ttk.Label(credits_frame, text="Follow author:", style="Small.TLabel").pack(side=tk.LEFT, padx=(0,5))
        ig_label = ttk.Label(credits_frame, text="Mahmoud Aboulnasr", style="Link.TLabel")
        ig_label.pack(side=tk.LEFT)
        ig_label.bind("<Button-1>", lambda e: self.open_link(APP_AUTHOR_IG))


        # --- FFmpeg Management Section ---
        ffmpeg_frame = ttk.LabelFrame(self.main_frame, text="FFmpeg Utility", padding="10 10 10 10")
        ffmpeg_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        ffmpeg_frame.columnconfigure(1, weight=1)

        self.ffmpeg_status_label = ttk.Label(ffmpeg_frame, text="Checking FFmpeg...", width=50) # Added width
        self.ffmpeg_status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        self.ffmpeg_action_button = ttk.Button(ffmpeg_frame, text="Help", command=self.ffmpeg_help, width=18)
        self.ffmpeg_action_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)

        self.ffmpeg_progress_label = ttk.Label(ffmpeg_frame, text="", style="Small.TLabel")
        self.ffmpeg_progress_label.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=(2,0))
        self.ffmpeg_progress_bar = ttk.Progressbar(ffmpeg_frame, length=200, mode="determinate", style="Horizontal.TProgressbar")
        # self.ffmpeg_progress_bar will be gridded by download function

        # --- Download Options Frame ---
        options_frame = ttk.LabelFrame(self.main_frame, text="Download Configuration", padding="10 10 10 10")
        options_frame.grid(row=2, column=0, columnspan=3, pady=(0,20), sticky=(tk.W, tk.E))
        for i in range(3): options_frame.columnconfigure(i, weight=1 if i==1 else 0) # Col 1 (entries) expands

        ttk.Label(options_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=7, padx=5)
        self.url_entry = ttk.Entry(options_frame, width=60) # Increased width
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=7, padx=5)
        
        ttk.Label(options_frame, text="Download Type:").grid(row=1, column=0, sticky=tk.W, pady=7, padx=5)
        self.download_type = ttk.Combobox(options_frame, values=["Video", "Audio", "Playlist"], state="readonly", width=20)
        self.download_type.set("Video")
        self.download_type.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=7, padx=5)
        
        ttk.Label(options_frame, text="Quality:").grid(row=2, column=0, sticky=tk.W, pady=7, padx=5)
        self.quality = ttk.Combobox(options_frame, values=["Best", "1080p", "720p", "480p", "360p"], state="readonly", width=20)
        self.quality.set("Best")
        self.quality.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=7, padx=5)
        
        self.download_type.bind("<<ComboboxSelected>>", self.toggle_quality)
        self.toggle_quality(None) 
        
        ttk.Label(options_frame, text="Save to:").grid(row=3, column=0, sticky=tk.W, pady=7, padx=5)
        self.output_entry = ttk.Entry(options_frame, width=50)
        self.output_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=7, padx=5)
        self.output_entry.insert(0, os.path.join(os.getcwd(), "AboulNasr_YT_Downloads")) # Changed default folder
        
        self.browse_button = ttk.Button(options_frame, text="Browse", command=self.browse_output_directory, width=12)
        self.browse_button.grid(row=3, column=2, sticky=tk.E, pady=7, padx=5)

        # --- Progress and Status ---
        progress_status_frame = ttk.LabelFrame(self.main_frame, text="Download Progress", padding="10 10 10 10")
        progress_status_frame.grid(row=3, column=0, columnspan=3, pady=(0,20), sticky=(tk.W, tk.E))
        progress_status_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(progress_status_frame, length=400, mode="determinate", style="Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, columnspan=3, pady=(10,5), padx=5, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(progress_status_frame, text="Ready.", wraplength=680) # Adjusted wraplength
        self.status_label.grid(row=1, column=0, columnspan=3, pady=5, padx=5, sticky=(tk.W, tk.E))
        
        # --- Action Buttons (Download & Cancel) ---
        action_buttons_frame = ttk.Frame(self.main_frame, style="TFrame")
        action_buttons_frame.grid(row=4, column=0, columnspan=3, pady=(10,0), sticky=tk.E)

        self.cancel_button = ttk.Button(action_buttons_frame, text="Cancel Download", command=self.request_cancel_download, style="Cancel.TButton", width=18)
        # self.cancel_button will be packed/gridded when download starts

        self.download_button = ttk.Button(action_buttons_frame, text="Download", command=self.start_download, style="Accent.TButton", width=18)
        self.download_button.pack(side=tk.RIGHT, padx=(10,0)) # Pack download button

        self.initial_ffmpeg_check()

    def open_link(self, url):
        webbrowser.open_new(url)

    def browse_output_directory(self):
        initial_dir = self.output_entry.get()
        if not os.path.isdir(initial_dir):
            initial_dir = os.getcwd()
        directory = filedialog.askdirectory(initialdir=initial_dir, title="Select Download Folder")
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)

    # --- FFmpeg methods (largely unchanged, slight UI updates if needed) ---
    def _get_ffmpeg_local_dir_base(self):
        if platform.system() == "Windows":
            path = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME.replace(" ", "_"))
        else:
            path = os.path.join(os.path.expanduser('~/.local/share'), APP_NAME.replace(" ", "_"))
        os.makedirs(os.path.join(path, "ffmpeg", "bin"), exist_ok=True)
        return os.path.join(path, "ffmpeg")

    def initial_ffmpeg_check(self):
        self.ffmpeg_path = shutil.which("ffmpeg")
        local_ffmpeg_exe = os.path.join(self._get_ffmpeg_local_dir_base(), "bin", "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")

        if self.ffmpeg_path:
            self.ffmpeg_status_label.config(text="FFmpeg (System PATH): " + os.path.dirname(self.ffmpeg_path)[:40]+"...")
            self.ffmpeg_action_button.config(text="FFmpeg Info", command=self.ffmpeg_info_found)
        elif os.path.exists(local_ffmpeg_exe):
            self.ffmpeg_path = local_ffmpeg_exe
            self.ffmpeg_status_label.config(text="FFmpeg found (App-Local).")
            self.ffmpeg_action_button.config(text="FFmpeg Info", command=self.ffmpeg_info_found_local)
        else:
            if platform.system() == "Windows":
                self.ffmpeg_status_label.config(text="FFmpeg not found. Needed for MP3/high quality.")
                self.ffmpeg_action_button.config(text="Download FFmpeg", command=self.prompt_ffmpeg_download_windows)
            else:
                self.ffmpeg_status_label.config(text="FFmpeg not in PATH. Install for full features.")
                self.ffmpeg_action_button.config(text="FFmpeg Help", command=self.ffmpeg_help_non_windows)

    def ffmpeg_info_found(self): messagebox.showinfo("FFmpeg Info", f"FFmpeg (System PATH):\n{self.ffmpeg_path}\nNo action needed.")
    def ffmpeg_info_found_local(self): messagebox.showinfo("FFmpeg Info", f"FFmpeg (App-Local):\n{self.ffmpeg_path}\nNo action needed.")
    def ffmpeg_help(self): messagebox.showinfo("FFmpeg Help", "FFmpeg is vital for MP3s and high-quality video merging.\nIf not found, some features might be limited or you'll be prompted to install/download it.")
    def ffmpeg_help_non_windows(self):
        msg = "FFmpeg not found in system PATH.\n\n"
        if platform.system() == "Linux": msg += "Install via package manager (e.g., `sudo apt install ffmpeg`).\n"
        elif platform.system() == "Darwin": msg += "Install via Homebrew (`brew install ffmpeg`).\n"
        msg += "Restart app after installation."
        messagebox.showinfo("FFmpeg Installation", msg)

    def prompt_ffmpeg_download_windows(self):
        if self.ffmpeg_download_in_progress: messagebox.showinfo("In Progress", "FFmpeg download active."); return
        if not platform.system() == "Windows": messagebox.showerror("Unsupported", "Auto FFmpeg download is for Windows only."); return
        
        response = messagebox.askyesno("Download FFmpeg?",
                                       f"Download FFmpeg for this app's use (approx. 50-80MB)?\nSaved in: {self._get_ffmpeg_local_dir_base()}\nThis won't alter system PATH.")
        if response:
            self.ffmpeg_download_in_progress = True
            self.ffmpeg_action_button.config(state="disabled")
            self.ffmpeg_status_label.config(text="Starting FFmpeg download...")
            self.ffmpeg_progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
            self.ffmpeg_progress_bar["value"] = 0
            self.ffmpeg_progress_label.config(text="0%")
            threading.Thread(target=self._execute_ffmpeg_download_windows, daemon=True).start()

    def _execute_ffmpeg_download_windows(self):
        # (This method is complex and remains largely the same for FFmpeg download logic)
        # Ensure UI updates are done via self.root.after
        ffmpeg_zip_path = os.path.join(self._get_ffmpeg_local_dir_base(), "ffmpeg-download.zip")
        ffmpeg_install_dir = self._get_ffmpeg_local_dir_base()
        ffmpeg_bin_dir = os.path.join(ffmpeg_install_dir, "bin")

        try:
            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="Downloading FFmpeg..."))
            response = requests.get(FFMPEG_DOWNLOAD_URL_WINDOWS, stream=True, timeout=30) # Added timeout
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(ffmpeg_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancel_download_event.is_set(): # Check for cancellation during FFmpeg download
                        raise UserWarning("FFmpeg download cancelled by user.")
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        self.root.after(0, lambda p=progress: self.ffmpeg_progress_bar.config(value=p))
                        self.root.after(0, lambda p=progress: self.ffmpeg_progress_label.config(text=f"{p:.0f}%"))
            
            if self.cancel_download_event.is_set(): raise UserWarning("FFmpeg download cancelled by user.")

            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="Extracting FFmpeg..."))
            self.root.after(0, lambda: self.ffmpeg_progress_bar.config(value=0))
            self.root.after(0, lambda: self.ffmpeg_progress_label.config(text="Extracting..."))

            with zipfile.ZipFile(ffmpeg_zip_path, 'r') as zip_ref:
                ffmpeg_exe_member, ffprobe_exe_member = None, None
                for member in zip_ref.namelist():
                    if member.endswith('/bin/ffmpeg.exe'): ffmpeg_exe_member = member
                    if member.endswith('/bin/ffprobe.exe'): ffprobe_exe_member = member
                if not ffmpeg_exe_member or not ffprobe_exe_member:
                    raise Exception("ffmpeg.exe or ffprobe.exe not in archive.")

                os.makedirs(ffmpeg_bin_dir, exist_ok=True)
                zip_ref.extract(ffmpeg_exe_member, ffmpeg_install_dir)
                zip_ref.extract(ffprobe_exe_member, ffmpeg_install_dir)
                
                extracted_ffmpeg_path = os.path.join(ffmpeg_install_dir, ffmpeg_exe_member)
                extracted_ffprobe_path = os.path.join(ffmpeg_install_dir, ffprobe_exe_member)
                final_ffmpeg_path = os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe')
                final_ffprobe_path = os.path.join(ffmpeg_bin_dir, 'ffprobe.exe')

                shutil.move(extracted_ffmpeg_path, final_ffmpeg_path)
                shutil.move(extracted_ffprobe_path, final_ffprobe_path)
                
                versioned_folder_name = os.path.dirname(os.path.dirname(ffmpeg_exe_member))
                if versioned_folder_name and os.path.isdir(os.path.join(ffmpeg_install_dir, versioned_folder_name)):
                    shutil.rmtree(os.path.join(ffmpeg_install_dir, versioned_folder_name), ignore_errors=True)

            self.ffmpeg_path = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="FFmpeg downloaded (App-Local)."))
            self.root.after(0, lambda: messagebox.showinfo("FFmpeg Ready", "FFmpeg successfully set up for this app."))
            self.root.after(0, lambda: self.ffmpeg_action_button.config(text="FFmpeg Info", command=self.ffmpeg_info_found_local))

        except UserWarning as e: # Catch our custom cancel
             self.root.after(0, lambda: self.ffmpeg_status_label.config(text=f"FFmpeg download: {e}"))
        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"FFmpeg download failed: {e}"))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="FFmpeg download failed."))
        except zipfile.BadZipFile:
            self.root.after(0, lambda: messagebox.showerror("Extraction Error", "FFmpeg extraction failed: Bad zip file."))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="FFmpeg extraction failed."))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("FFmpeg Setup Error", f"FFmpeg setup error: {e}"))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(text="FFmpeg setup error."))
        finally:
            self.ffmpeg_download_in_progress = False
            self.root.after(0, lambda: self.ffmpeg_action_button.config(state="normal"))
            self.root.after(0, lambda: self.ffmpeg_progress_bar.grid_remove())
            self.root.after(0, lambda: self.ffmpeg_progress_label.config(text=""))
            if os.path.exists(ffmpeg_zip_path):
                try: os.remove(ffmpeg_zip_path)
                except OSError as e: print(f"Warning: Could not remove {ffmpeg_zip_path}: {e}")
            self.cancel_download_event.clear() # Clear event for FFmpeg download

    def toggle_quality(self, event):
        # (Same as before)
        if self.download_type.get() == "Audio":
            self.quality.configure(state="disabled"); self.quality.set("Best") 
        else:
            self.quality.configure(state="readonly")
            if self.quality.get() == "": self.quality.set("Best")

    def progress_hook(self, d):
        if self.cancel_download_event.is_set():
            # This is a way to tell yt-dlp to stop. It will raise an error.
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        if not self.root.winfo_exists(): return
        status = d.get("status")
        # (Rest of progress_hook largely same, ensure UI updates via root.after)
        if status == "downloading":
            percent_str = d.get("_percent_str", "0%").strip().replace('%', '')
            item_title = d.get('info_dict', {}).get('title', os.path.basename(d.get('filename', d.get('tmpfilename', 'item'))))[:40]
            pl_idx, pl_count = d.get('playlist_index'), d.get('playlist_count')
            text = f"Item {pl_idx}/{pl_count} " if pl_idx else ""
            text += f"({item_title}...): {d.get('_percent_str', '0%')}" if len(item_title) == 40 else f"({item_title}): {d.get('_percent_str', '0%')}"
            
            def update_ui_dl():
                try:
                    if percent_str and percent_str.replace('.', '', 1).isdigit(): self.progress["value"] = float(percent_str)
                    self.status_label["text"] = text
                except Exception: pass # Ignore if widget destroyed or value error
            self.root.after(0, update_ui_dl)

        elif status == "finished":
            item_title = d.get('info_dict', {}).get('title', os.path.basename(d.get('filename', 'item')))[:50]
            text = f"Finished: {item_title}" + ("..." if len(item_title) == 50 else "")
            if d.get('type') == 'playlist' and d.get('playlist_index') is None:
                 text = f"Playlist finished: {d.get('info_dict',{}).get('title', 'playlist')}"
            def update_ui_fin(): self.status_label["text"] = text; self.progress["value"] = 100
            self.root.after(0, update_ui_fin)
        
        elif status == "error":
            def update_ui_err(): self.status_label["text"] = "Error during an item download."
            self.root.after(0, update_ui_err)

    def _finalize_download_ui(self, success=True, message=""):
        """Helper to reset UI elements after download attempt."""
        self.download_button.config(state="normal")
        self.cancel_button.pack_forget() # Hide cancel button
        self.cancel_download_event.clear()
        self.download_thread = None
        if self.root.winfo_exists():
            if success:
                self.status_label.config(text=message or "Download Process Complete!")
                self.progress.config(value=100)
            else:
                self.status_label.config(text=message or "Download Failed or Cancelled.")
                if "Cancelled" not in (message or ""): # Don't reset progress if cancelled mid-way
                    self.progress.config(value=0)

    def request_cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.status_label.config(text="Cancellation requested...")
            self.cancel_download_event.set()
            self.cancel_button.config(state="disabled", text="Cancelling...")


    def download(self, url, output_path, download_type, quality_selection):
        try:
            os.makedirs(output_path, exist_ok=True)
            ydl_opts = {
                "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
                "progress_hooks": [self.progress_hook],
                "nocheckcertificate": True, "ignoreerrors": False,
            }
            if self.ffmpeg_path: ydl_opts['ffmpeg_location'] = self.ffmpeg_path
            # (Format selection logic same as before)
            if download_type == "Audio":
                ydl_opts.update({"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}], "keepvideo": False})
            else:
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=webm]+bestaudio[ext=webm]/best[vcodec!=none][acodec!=none]/bestvideo+bestaudio/best"
                if quality_selection != "Best":
                    qv = quality_selection[:-1]
                    fmt = f"bestvideo[height<={qv}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={qv}][ext=webm]+bestaudio[ext=webm]/bestvideo[height<={qv}][vcodec!=none][acodec!=none]/bestvideo[height<={qv}]+bestaudio/best[height<={qv}]"
                ydl_opts["format"] = fmt
                if download_type == "Playlist": ydl_opts.update({'noplaylist': False, 'ignoreerrors': True})
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not self.cancel_download_event.is_set(): # Only show success if not cancelled
                self.root.after(0, lambda: messagebox.showinfo("Success", "Download process completed!"))
                self.root.after(0, self._finalize_download_ui, True, "Download Process Complete!")

        except yt_dlp.utils.DownloadCancelled: # Our custom cancel
            self.root.after(0, self._finalize_download_ui, False, "Download Cancelled by User.")
        except yt_dlp.utils.DownloadError as e:
            # (FFmpeg error handling largely same, ensure root.after)
            err_msg = f"Download failed: {e}"
            # ... (more specific error messages like before) ...
            if "ffmpeg" in str(e).lower() and ("not found" in str(e).lower() or "is not installed" in str(e).lower()):
                err_msg = "FFmpeg needed but not found. Use FFmpeg Utility section." # Simplified for brevity
            self.root.after(0, lambda m=err_msg: messagebox.showerror("Download Error", m))
            self.root.after(0, self._finalize_download_ui, False, "Download Failed.")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Unexpected Error", f"Error: {e}"))
            self.root.after(0, self._finalize_download_ui, False, "Unexpected Error Occurred.")
        # 'finally' block is removed, _finalize_download_ui handles UI reset from specific exit points.


    def start_download(self):
        if self.ffmpeg_download_in_progress: messagebox.showwarning("Busy", "FFmpeg setup active."); return
        if self.download_thread and self.download_thread.is_alive(): messagebox.showwarning("Busy", "Download already in progress."); return

        url = self.url_entry.get().strip()
        output_path = self.output_entry.get().strip()
        if not url: messagebox.showerror("Input Error", "YouTube URL is required."); return
        if not output_path: messagebox.showerror("Input Error", "Output directory is required."); return
            
        self.cancel_download_event.clear() # Reset event for new download
        self.progress["value"] = 0
        self.status_label["text"] = "Preparing download..."
        self.download_button.config(state="disabled")
        self.cancel_button.config(text="Cancel Download", state="normal") # Enable and reset cancel button text
        self.cancel_button.pack(side=tk.LEFT, padx=(0,10)) # Show cancel button next to download button
        
        self.download_thread = threading.Thread(
            target=self.download,
            args=(url, output_path, self.download_type.get(), self.quality.get()),
            daemon=True
        )
        self.download_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()