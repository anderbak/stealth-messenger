import tkinter as tk
import tkinter.ttk as ttk
import ctypes
import subprocess
import time
import os
import tempfile
import base64
import cv2
import threading
import re
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
from openai import OpenAI
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pytesseract

class StealthMessenger:
    def __init__(self):
        self.message_window = None
        self.bg_color = 'white'
        self.fg_color = 'black'
        self.msg_x, self.msg_y = 250, 250
        self.font_size = 14
        self.alpha_value = 0.05
        self.close_message_window_button = None
        self.video_process = None
        self.start_video_button = None
        self.stop_video_button = None
        self.capture_frame_button = None
        self.frame_filename = None
        self.captured_frames = []  # Store captured frame filenames
        self.ocr_texts = []  # Add this attribute to store OCR text for each frame
        self.current_frame_index = -1  # Track the current frame index
        self.SAVE_FOLDER = os.path.join(tempfile.gettempdir(), "captured_frames")
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)
        self.RESOURCE_FILES = None
        self.API_KEY = None
        self.session_key = None
        self.encrypted_api_key = None
        self.nonce = None
        self.saved_image_prompt = ""
        self.saved_prompt = ""
        self.video_device_var = None
        self.video_device_dropdown = None
        self.query_answers = []  # Add this attribute to store query answers

app = StealthMessenger()

def display_message(message):
    if app.message_window:
        app.message_window.destroy()
    
    app.message_window = tk.Toplevel()
    app.message_window.title("")
    app.message_window.attributes('-topmost', True)
    app.message_window.overrideredirect(True)
    app.message_window.attributes('-alpha', app.alpha_value)
    app.message_window.configure(bg=app.bg_color)
    
    label = tk.Label(app.message_window, text=message, font=("Roboto", app.font_size), fg=app.fg_color, bg=app.bg_color, wraplength=400, justify="left")
    label.pack(padx=10, pady=10)
    
    app.message_window.update_idletasks()
    width = label.winfo_reqwidth() + 20
    height = label.winfo_reqheight() + 20
    app.message_window.geometry(f"{width}x{height}+{app.msg_x}+{app.msg_y}")
    
    hwnd = ctypes.windll.user32.GetParent(app.message_window.winfo_id())
    style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
    
    app.close_message_window_button.state(["!disabled"])
    
def close_message_window():
    if app.message_window:
        app.message_window.destroy()
        app.message_window = None
        
    app.close_message_window_button.state(["disabled"])
    
def set_mode(mode):
    if mode == 'light':
        app.bg_color = 'white'
        app.fg_color = 'black'
    else:
        app.bg_color = 'black'
        app.fg_color = 'white'
    update_message_window()   
 
def update_message_window():
    if app.message_window:
        display_message(app.message_window.children['!label'].cget("text"))

def move_message(dx, dy):
    app.msg_x += dx
    app.msg_y += dy

    app.position_label.config(text=f"{app.msg_x}:{app.msg_y}")

    if app.message_window is not None:
        app.message_window.geometry(f"+{app.msg_x}+{app.msg_y}")

def change_font_size(delta):
    app.font_size += delta
    app.font_size = max(6, min(app.font_size, 72))

    app.text_size_label.config(text=f"Size: {app.font_size}")

    if app.message_window is not None:
        for widget in app.message_window.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(font=("Roboto", app.font_size))

        app.message_window.update_idletasks()
        width = app.message_window.winfo_reqwidth() + 20
        height = app.message_window.winfo_reqheight() + 20
        app.message_window.geometry(f"{width}x{height}+{app.msg_x}+{app.msg_y}")

def change_transparency(delta):
    app.alpha_value = max(0.05, min(app.alpha_value + delta, 1.0))

    app.alpha_value_label.config(text=f"Alpha: {int(app.alpha_value * 100)}%")

    if app.message_window is not None:
        app.message_window.attributes('-alpha', app.alpha_value)

def start_video():
    if app.video_process:
        messagebox.showinfo("Info", "FFplay is already running.")
        return

    selected_device = app.video_device_var.get()

    command = ["ffplay", "-f", "dshow", "-rtbufsize", "100M",
               "-video_size", "1920x1080", "-framerate", "30",
               "-i", f"video={selected_device}"]

    try:
        app.video_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        app.start_video_button.config(state=tk.DISABLED)
        app.stop_video_button.config(state=tk.NORMAL)
        app.capture_frame_button.config(state=tk.NORMAL)

    except FileNotFoundError:
        messagebox.showerror("Error", "FFplay not found. Make sure it's installed.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start FFplay: {e}")

def stop_video():
    if app.video_process:
        app.video_process.terminate()
        time.sleep(1)

        if app.video_process.poll() is None:
            app.video_process.kill()

        app.video_process = None

    app.start_video_button.config(state=tk.NORMAL)
    app.stop_video_button.config(state=tk.DISABLED)
    app.capture_frame_button.config(state=tk.DISABLED)

def capture_frame():
    app.input_entry_var.set("")
    selected_device = app.video_device_var.get()
    if selected_device == "No camera available":
        messagebox.showerror("Error", "No camera available to capture frames.")
        return

    app.frame_filename = os.path.join(app.SAVE_FOLDER, f"frame_{int(time.time())}.jpg")

    ffmpeg_command = [
        "ffmpeg", "-y", "-f", "gdigrab", "-framerate", "1",
        "-i", f"title=video={selected_device}",
        "-frames:v", "1", "-q:v", "2", app.frame_filename
    ]

    try:
        app.api_status_var.set("OpenAI API Status: Capturing frame")
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if os.path.exists(app.frame_filename):
            app.captured_frames.append(app.frame_filename)
            app.current_frame_index = len(app.captured_frames) - 1
            load_image_from_index()
            update_navigation_buttons()

            def process_and_update_status():
                process_frame_in_background(app.frame_filename)
                app.api_status_var.set("OpenAI API Status: Idle")

            threading.Thread(target=process_and_update_status, daemon=True).start()
        else:
            messagebox.showerror("Error", "FFmpeg did not save the frame.")
            app.api_status_var.set("OpenAI API Status: Idle")

    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to capture frame: {e}")
        app.api_status_var.set("OpenAI API Status: Idle")

def process_frame_in_background(image_path):
    app.api_status_var.set("OpenAI API Status: Performing OCR")
    extracted_text = perform_local_ocr(image_path)

    if extracted_text:
        update_ocr_text_display()

def perform_local_ocr(image_path):
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        img = Image.open(image_path)
        ocr_text = pytesseract.image_to_string(img)

        if not ocr_text.strip():
            ocr_text = "No text detected."

        app.ocr_texts.append(ocr_text.strip())

        return ocr_text.strip()
        
    except Exception as e:
        messagebox.showerror("Error", f"Local OCR failed: {e}")
        return None

def load_image_from_index():
    if 0 <= app.current_frame_index < len(app.captured_frames):
        try:
            frame_path = app.captured_frames[app.current_frame_index]
            img = Image.open(frame_path)

            new_size = (640, 360)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            img_tk = ImageTk.PhotoImage(img)

            app.image_label.config(image=img_tk, text="")
            app.image_label.image = img_tk

            update_ocr_text_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    else:
        app.image_label.config(image="", text="No Image Loaded")
        app.image_label.image = None
    update_ocr_text_display()

def update_ocr_text_display():
    if 0 <= app.current_frame_index < len(app.ocr_texts):
        ocr_text = app.ocr_texts[app.current_frame_index]
    else:
        ocr_text = "No OCR text available."

    app.ocr_textbox.delete("1.0", tk.END)
    app.ocr_textbox.insert("1.0", ocr_text)

def update_navigation_buttons():
    if app.current_frame_index > 0:
        app.back_button.config(state=tk.NORMAL)
    else:
        app.back_button.config(state=tk.DISABLED)

    if app.current_frame_index < len(app.captured_frames) - 1:
        app.next_button.config(state=tk.NORMAL)
    else:
        app.next_button.config(state=tk.DISABLED)

    if 0 <= app.current_frame_index < len(app.captured_frames):
        app.query_button.config(state=tk.NORMAL)
    else:
        app.query_button.config(state=tk.DISABLED)

def show_previous_image():
    if app.current_frame_index > 0:
        app.current_frame_index -= 1
        load_image_from_index()
        if 0 <= app.current_frame_index < len(app.query_answers):
            app.input_entry_var.set(app.query_answers[app.current_frame_index])
        else:
            app.input_entry_var.set("")
    else:
        messagebox.showinfo("Info", "No previous image available.")
    update_navigation_buttons()

def show_next_image():
    if app.current_frame_index < len(app.captured_frames) - 1:
        app.current_frame_index += 1
        load_image_from_index()
        if 0 <= app.current_frame_index < len(app.query_answers):
            app.input_entry_var.set(app.query_answers[app.current_frame_index])
        else:
            app.input_entry_var.set("")
    else:
        messagebox.showinfo("Info", "No next image available.")
    update_navigation_buttons()

def load_image():
    try:
        if not os.path.exists(app.frame_filename):
            return

        img = Image.open(app.frame_filename)

        img_width, img_height = img.size
        new_size = (640, 360)
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        img_tk = ImageTk.PhotoImage(img)

        app.image_label.config(image=img_tk, text="")
        app.image_label.image = img_tk

    except Exception as e:
        return

def select_files():
    file_paths = filedialog.askopenfilenames(
        title="Select Files",
        filetypes=[("All Files", "*.*"), ("Text Files", "*.txt"), ("Images", "*.png;*.jpg;*.jpeg"), ("PDF Files", "*.pdf")]
    )

    if file_paths:
        return file_paths
    else:
        return []

def load_resources():
    if not app.RESOURCE_FILES:
        return ""
    
    combined_text = ""
    for file in os.listdir(app.RESOURCE_FILES):
        if file.endswith(".txt"):
            with open(os.path.join(app.RESOURCE_FILES, file), "r", encoding="utf-8") as f:
                combined_text += f.read() + "\n\n"
    return combined_text

def openai_query(ocr_text):
    decrypted_key = get_decrypted_api_key()
    if not decrypted_key:
        return None

    client = OpenAI(api_key=decrypted_key)

    resources_text = load_resources().strip()

    user_prompt = app.saved_prompt.strip() if app.saved_prompt else "Answer this query based on the given reference material."

    prompt = f"{user_prompt}\n\n**Query Text:**\n{ocr_text}"
    if resources_text:
        prompt += f"\n\n**Reference Material:**\n{resources_text}"

    try:
        app.api_status_var.set("OpenAI API Status: Running query")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5
        )

        query_response = response.choices[0].message.content.strip()
        return query_response

    except Exception as e:
        messagebox.showerror("Error", f"OpenAI API Error: {e}")
        return

def set_api_key():
    if app.session_key is None:
        app.session_key = AESGCM.generate_key(bit_length=128)

    key_window = tk.Toplevel()
    key_window.title("Set OpenAI API Key")
    key_window.geometry("400x150")
    key_window.attributes('-topmost', True)

    ttk.Label(key_window, text="Enter OpenAI API Key:").pack(pady=10)
    
    api_key_var = tk.StringVar()
    api_entry = ttk.Entry(key_window, textvariable=api_key_var, show="*", width=40)
    api_entry.pack(pady=5)
    api_entry.focus()

    def submit_key():
        api_key_plaintext = api_key_var.get().strip().encode()

        if not api_key_plaintext:
            messagebox.showerror("Error", "API Key cannot be empty.")
            return

        aes_gcm = AESGCM(app.session_key)
        app.nonce = os.urandom(12)
        app.encrypted_api_key = aes_gcm.encrypt(app.nonce, api_key_plaintext, None)

        key_window.destroy()
        messagebox.showinfo("Success", "API Key encrypted and stored for this session.")

    ttk.Button(key_window, text="Save", command=submit_key).pack(pady=10)

def enumerate_video_devices():
    available_devices = []
    
    try:
        output = subprocess.check_output('ffmpeg -list_devices true -f dshow -i dummy', stderr=subprocess.STDOUT, text=True, shell=True)

        pattern = r'\[dshow @ [^\]]+\] "([^"]+)" \(video\)'

        for line in output.splitlines():
            match = re.search(pattern, line)
            if match:
                available_devices.append(match.group(1))

    except subprocess.CalledProcessError:
        pass
    except Exception:
        pass

    return available_devices if available_devices else ["No camera found"]
    
def get_decrypted_api_key():
    if not app.session_key or not app.encrypted_api_key or not app.nonce:
        messagebox.showerror("Error", "No API Key Set. Please set it first.")
        return None

    try:
        aes_gcm = AESGCM(app.session_key)
        decrypted_api_key = aes_gcm.decrypt(app.nonce, app.encrypted_api_key, None)
        return decrypted_api_key.decode()

    except Exception as e:
        messagebox.showerror("Error", f"Decryption failed: {e}")
        return None

def update_video_device_dropdown():
    def enumerate_and_update():
        video_devices = enumerate_video_devices()
        app.video_device_dropdown["values"] = video_devices
        
        if not video_devices or "No camera found" in video_devices:
            app.video_device_var.set("No camera available")
            app.start_video_button.config(state=tk.DISABLED)
        else:
            app.video_device_var.set(video_devices[0])
            app.start_video_button.config(state=tk.NORMAL)

    threading.Thread(target=enumerate_and_update, daemon=True).start()

def open_settings_window():
    settings_window = tk.Toplevel()
    settings_window.title("Settings")
    settings_window.geometry("1000x800")
    settings_window.resizable(False, False)
    settings_window.grab_set()

    api_key_frame = ttk.Frame(settings_window)
    api_key_frame.pack(anchor="w", padx=10, pady=5, fill="x")

    ttk.Label(api_key_frame, text="OpenAI API Key:", font=("Roboto", 10)).pack(side="left", padx=(0, 5))
    
    api_key_var = tk.StringVar()
    api_entry = ttk.Entry(api_key_frame, textvariable=api_key_var, show="*", width=40)
    api_entry.pack(side="left", fill="x", expand=True)
    api_entry.focus()

    def submit_key():
        api_key_plaintext = api_key_var.get().strip().encode()

        if not api_key_plaintext:
            messagebox.showerror("Error", "API Key cannot be empty.")
            return

        if app.session_key is None:
            app.session_key = AESGCM.generate_key(bit_length=128)

        aes_gcm = AESGCM(app.session_key)
        app.nonce = os.urandom(12)
        app.encrypted_api_key = aes_gcm.encrypt(app.nonce, api_key_plaintext, None)

        api_key_var.set("")

    save_button = ttk.Button(api_key_frame, text="Save API Key", command=submit_key)
    save_button.pack(side="left", padx=(5, 0))

    prompt_frame = ttk.LabelFrame(settings_window, text="Prompt Settings")
    prompt_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(prompt_frame, text="OpenAI Query:", font=("Arial", 10)).pack(pady=(10, 0), anchor="w", padx=10)
    query_text = tk.Text(prompt_frame, height=5, wrap="word")
    query_text.pack(fill="both", expand=True, padx=10, pady=5)
    query_text.insert("1.0", app.saved_prompt)

    def save_prompt():
        app.saved_prompt = query_text.get("1.0", "end").strip()

    save_prompt_button = ttk.Button(prompt_frame, text="Save Prompt", command=save_prompt, width=13)
    save_prompt_button.pack(side="left", padx=5, pady=5)

    select_files_button = ttk.Button(prompt_frame, text="Select Files", command=select_files, width=13)
    select_files_button.pack(side="left", padx=5, pady=5)

    video_frame = ttk.LabelFrame(settings_window, text="Video Device Controls")
    video_frame.pack(fill="x", padx=10, pady=10)

    app.video_device_var = tk.StringVar(value="Scanning...")
    app.video_device_dropdown = ttk.Combobox(video_frame, textvariable=app.video_device_var, state="readonly", width=30)
    app.video_device_dropdown.grid(row=0, column=0, padx=5, pady=5)

    refresh_button = ttk.Button(video_frame, text="Refresh", command=update_video_device_dropdown, width=10)
    refresh_button.grid(row=0, column=1, padx=5, pady=5)

    app.start_video_button = ttk.Button(video_frame, text="Start Video", command=start_video, width=10)
    app.start_video_button.grid(row=0, column=2, padx=5, pady=5)
    app.start_video_button.state(["!disabled"])

    app.stop_video_button = ttk.Button(video_frame, text="Stop Video", command=stop_video, width=10)
    app.stop_video_button.grid(row=0, column=3, padx=5, pady=5)
    app.stop_video_button.state(["disabled"])

    threading.Thread(target=update_video_device_dropdown, daemon=True).start()

def run_query():
    if 0 <= app.current_frame_index < len(app.ocr_texts):
        ocr_text = app.ocr_textbox.get("1.0", tk.END).strip()

        if not ocr_text:
            messagebox.showerror("Error", "No text available in the OCR textbox.")
            return
        
        app.api_status_var.set("OpenAI API Status: Running query")

        app.ocr_texts[app.current_frame_index] = ocr_text

        query_answer = openai_query(ocr_text)

        if query_answer:
            app.input_entry_var.set(query_answer)
            app.query_answers.append(query_answer)
            app.api_status_var.set("OpenAI API Status: Idle")
        else:
            messagebox.showerror("Error", "Failed to get a response from OpenAI.")
            app.api_status_var.set("OpenAI API Status: Idle")
    else:
        messagebox.showinfo("Info", "No valid frame selected for rerunning the query.")
        app.api_status_var.set("OpenAI API Status: Idle")

def open_input_window():
    input_window = tk.Tk()
    input_window.title("Stealth Messenger")
    input_window.geometry("1200x600+200+100")
    input_window.resizable(False, False)
    #input_window.attributes('-topmost', True)

    style = ttk.Style()
    style.configure("TButton", font=("Roboto", 10), padding=5)
    style.configure("TLabel", font=("Roboto", 11))

    main_frame = ttk.Frame(input_window)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    controls_frame = ttk.Frame(main_frame)
    controls_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=10, pady=10)

    image_frame = ttk.Frame(main_frame)
    image_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=2, pady=2)

    message_frame = ttk.Frame(controls_frame)
    message_frame.pack(fill="x", padx=10, pady=5)

    ttk.Label(message_frame, text="Message:").pack(side=tk.LEFT, padx=(0, 5))

    app.input_entry_var = tk.StringVar()
    input_entry = ttk.Entry(message_frame, width=40, textvariable=app.input_entry_var)
    input_entry.pack(side=tk.LEFT, fill="x", expand=True)
    input_entry.focus()

    def submit_message():
        message = app.input_entry_var.get()
        if message:
            display_message(message)

    button_frame = ttk.Frame(controls_frame)
    button_frame.pack(pady=5)

    ttk.Button(button_frame, text="Send", command=submit_message, width=16).pack(side=tk.LEFT, padx=5)

    app.close_message_window_button = ttk.Button(button_frame, text="Close", command=close_message_window, width=16)
    app.close_message_window_button.pack(side=tk.LEFT, padx=5)
    app.close_message_window_button.state(["disabled"])

    app.api_status_var = tk.StringVar(value="OpenAI API Status: Idle")
    api_status_label = ttk.Label(controls_frame, textvariable=app.api_status_var, font=("Arial", 10), foreground="gray")
    api_status_label.pack(pady=(5, 0))

    move_frame = ttk.LabelFrame(controls_frame, text="Message Window")
    move_frame.pack(pady=5, padx=10, anchor="center")

    mode_var = tk.StringVar(value='light')
    ttk.Radiobutton(move_frame, text="Light", variable=mode_var, value='light', command=lambda: set_mode('light')).grid(row=0, column=6, padx=5)
    ttk.Radiobutton(move_frame, text="Dark", variable=mode_var, value='dark', command=lambda: set_mode('dark')).grid(row=1, column=6, padx=5)

    ttk.Button(move_frame, text="Up", command=lambda: move_message(0, -10), width=8).grid(row=0, column=2, pady=2)
    ttk.Button(move_frame, text="Left", command=lambda: move_message(-10, 0), width=8).grid(row=1, column=0, padx=2)
    ttk.Button(move_frame, text="Right", command=lambda: move_message(10, 0), width=8).grid(row=1, column=3, padx=2)
    ttk.Button(move_frame, text="Down", command=lambda: move_message(0, 10), width=8).grid(row=2, column=2, pady=2)

    app.position_label = ttk.Label(move_frame, text=f"{app.msg_x}:{app.msg_y}", width=8, anchor="center", justify="center")
    app.position_label.grid(row=1, column=2, padx=2, pady=2, sticky="ew")

    ttk.Button(move_frame, text="Dec Text", command=lambda: change_font_size(-2), width=9).grid(row=2, column=5, padx=2)
    ttk.Button(move_frame, text="Inc Text", command=lambda: change_font_size(2), width=9).grid(row=0, column=5, padx=2)

    app.text_size_label = ttk.Label(move_frame, text=f"Size: {app.font_size}", width=9, anchor="center", justify="center")
    app.text_size_label.grid(row=1, column=5, padx=2, pady=2, sticky="ew")

    ttk.Button(move_frame, text="Inc Viz", command=lambda: change_transparency(0.05), width=9).grid(row=0, column=4, padx=2)
    ttk.Button(move_frame, text="Dec Viz", command=lambda: change_transparency(-0.05), width=9).grid(row=2, column=4, padx=2)

    app.alpha_value_label = ttk.Label(move_frame, text=f"Alpha: {int(app.alpha_value * 100)}%", width=9, anchor="center", justify="center")
    app.alpha_value_label.grid(row=1, column=4, padx=2, pady=2, sticky="ew")

    settings_button = ttk.Button(controls_frame, text="Settings", command=open_settings_window)
    settings_button.pack(pady=10)

    app.image_label = tk.Label(image_frame, text="No Image Loaded", bg="gray")
    app.image_label.pack(fill="both", expand=True, padx=10, pady=10)

    navigation_frame = ttk.Frame(image_frame)
    navigation_frame.pack(fill="x", pady=(5, 0))

    app.back_button = ttk.Button(navigation_frame, text="Back", command=show_previous_image)
    app.back_button.pack(side=tk.LEFT, padx=5, pady=5)

    app.next_button = ttk.Button(navigation_frame, text="Next", command=show_next_image)
    app.next_button.pack(side=tk.LEFT, padx=5, pady=5)

    app.query_button = ttk.Button(navigation_frame, text="Query", command=run_query)
    app.query_button.pack(side=tk.RIGHT, padx=5, pady=5)

    app.capture_frame_button = ttk.Button(navigation_frame, text="Capture Frame", command=capture_frame)
    app.capture_frame_button.pack(side=tk.RIGHT, padx=5, pady=5)

    app.capture_frame_button.state(["disabled"])

    app.ocr_textbox = tk.Text(image_frame, height=10, wrap="word", font=("Arial", 10))
    app.ocr_textbox.pack(fill="x", padx=10, pady=(5, 10))
    app.ocr_textbox.insert("1.0", "No OCR text available.")

    update_navigation_buttons()

    input_window.mainloop()

open_input_window()
