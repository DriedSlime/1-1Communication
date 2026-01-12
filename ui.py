# ui.py
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import io

from config import DEFAULT_SERVER_HOST


class AppUI:
    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.title("1:1 Video Chat + H.263 Stream + File Transfer + Text Chat")
        self.root.geometry("960x680")
        self.root.protocol("WM_DELETE_WINDOW", self.app.close)

        # 상단 컨트롤 프레임
        control_frame = tk.Frame(self.root, bg="#f0f0f0", pady=8, bd=2, relief=tk.GROOVE)
        control_frame.pack(fill=tk.X)

        # Connection
        group_conn = tk.LabelFrame(control_frame, text="Connection", padx=6, pady=6)
        group_conn.pack(side=tk.LEFT, padx=6)

        tk.Label(group_conn, text="Server IP:").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(group_conn, width=14)
        self.ip_entry.insert(0, DEFAULT_SERVER_HOST)
        self.ip_entry.pack(side=tk.LEFT)

        tk.Button(group_conn, text="Connect", command=self.app.connect_server,
                  bg="#8ee58e").pack(side=tk.LEFT)
        tk.Button(group_conn, text="Disconnect", command=self.app.disconnect_server,
                  bg="#f5a3a3").pack(side=tk.LEFT)

        # Source / File
        group_mode = tk.LabelFrame(control_frame, text="Source", padx=6, pady=6)
        group_mode.pack(side=tk.LEFT, padx=6)

        self.combo_mode = ttk.Combobox(
            group_mode,
            values=["Camera", "Video File", "Image File", "Audio Visualizer"],
            state="readonly", width=12
        )
        self.combo_mode.current(0)
        self.combo_mode.pack(side=tk.LEFT, padx=6)

        # CAMERA BUTTON GROUP 
        frame_cam = tk.Frame(group_mode)
        frame_cam.pack(side=tk.LEFT, padx=6)

        tk.Button(
            frame_cam, text="Start Camera",
            command=self.app.start_camera,
            bg="#d2dcfc", width=10
        ).pack(pady=0)

        tk.Button(
            frame_cam, text="Stop Camera",
            command=self.app.stop_camera,
            bg="#f5a3a3", width=10
        ).pack(pady=0)

        # MIC BUTTON GROUP
        frame_mic = tk.Frame(group_mode)
        frame_mic.pack(side=tk.LEFT, padx=6)

        tk.Button(
            frame_mic, text="Start Mic",
            command=self.app.start_audio,
            bg="#d2dcfc", width=10
        ).pack(pady=0)

        tk.Button(
            frame_mic, text="Stop Mic",
            command=self.app.stop_audio,
            bg="#f5a3a3", width=10
        ).pack(pady=0)

        # FILE BUTTONS
        frame_file = tk.Frame(group_mode)
        frame_file.pack(side=tk.LEFT, padx=6)

        tk.Button(frame_file, text="Load File", command=self.app.load_file).pack(pady=2)
        tk.Button(frame_file, text="Send Image", command=self.app.compress_and_send_with_quality).pack(pady=2)
        tk.Button(frame_file, text="Send Video", command=self.app.compress_and_send_h263_video).pack(pady=2)
        
        # Quality / Filter
        group_effect = tk.LabelFrame(control_frame, text="Quality / Filter", padx=6, pady=6)
        group_effect.pack(side=tk.LEFT, padx=6)
        tk.Label(group_effect, text="Quality:").pack(side=tk.LEFT)
        self.scale_quality = tk.Scale(
            group_effect, from_=10, to=95, orient=tk.HORIZONTAL,
            showvalue=0, length=100, command=self.app.update_quality
        )
        self.scale_quality.set(self.app.compression_quality)
        self.scale_quality.pack(side=tk.LEFT, padx=6)
        tk.Label(group_effect, text="Filter:").pack(side=tk.LEFT)
        self.combo_filter = ttk.Combobox(
            group_effect,
            values=["None", "Gray", "Canny(Edge)", "Inverse", "Face Detect", "Blur"],
            state="readonly", width=16
        )
        self.combo_filter.current(0)
        self.combo_filter.pack(side=tk.LEFT, padx=6)
        self.combo_filter.bind("<<ComboboxSelected>>", self.app.change_filter)

        # 메인 영역 (Local / Remote / Chat)
        main_frame = tk.Frame(self.root, bg="#202020")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame, bg="black", bd=2, relief=tk.SUNKEN)
        left_frame.place(relx=0.0, rely=0.0, relwidth=0.4, relheight=1.0)
        tk.Label(left_frame, text="[ Local Source ]", fg="yellow", bg="black").pack(anchor=tk.NW)
        self.lbl_local = tk.Label(left_frame, bg="black")
        self.lbl_local.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        middle_frame = tk.Frame(main_frame, bg="black", bd=2, relief=tk.SUNKEN)
        middle_frame.place(relx=0.4, rely=0.0, relwidth=0.4, relheight=1.0)
        tk.Label(middle_frame, text="[ Remote Received ]", fg="cyan", bg="black").pack(anchor=tk.NW)
        self.lbl_remote = tk.Label(middle_frame, bg="black")
        self.lbl_remote.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        right_frame = tk.Frame(main_frame, bg="#1a1a1a", bd=2, relief=tk.SUNKEN)
        right_frame.place(relx=0.8, rely=0.0, relwidth=0.2, relheight=1.0)
        tk.Label(right_frame, text="Chat", fg="white", bg="#222").pack(fill=tk.X)
        self.chat_box = tk.Text(right_frame, bg="#111", fg="white", wrap=tk.WORD, state='disabled')
        self.chat_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        entry_frame = tk.Frame(right_frame, bg="#222")
        entry_frame.pack(fill=tk.X, padx=6, pady=6)
        self.chat_entry = tk.Entry(entry_frame, bg="#333", fg="white")
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", self.app.on_enter_pressed)
        tk.Button(entry_frame, text="Send", bg="#444", fg="white",
                  command=self.app.send_chat).pack(side=tk.RIGHT)

        self.status_bar = tk.Label(
            self.root, text="Ready.", bd=1, relief=tk.SUNKEN,
            anchor=tk.W, bg="#ddd", font=("Arial", 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # --- 이미지 갱신 헬퍼 ---
    def show_local_bgr(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = img.resize((440, 560))
            imgtk = ImageTk.PhotoImage(img)
            self.lbl_local.configure(image=imgtk)
            self.lbl_local.image = imgtk
        except Exception as e:
            print("show_local_frame error:", e)

    def show_remote_jpeg(self, jpeg_bytes: bytes):
        try:
            img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
            img = img.resize((440, 560))
            imgtk = ImageTk.PhotoImage(img)
            self.lbl_remote.configure(image=imgtk)
            self.lbl_remote.image = imgtk
        except Exception as e:
            print("show_remote_frame error:", e)

    def clear_local(self):
        self.lbl_local.configure(image='')
        self.lbl_local.image = None
