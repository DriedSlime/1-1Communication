# chat.py
from config import TYPE_TEXT
from network import send_packet

class ChatManager:
    def __init__(self, app):
        self.app = app  # main.App

    def append(self, text: str):
        try:
            box = self.app.ui.chat_box
            box.configure(state='normal')
            box.insert('end', text + '\n')
            box.configure(state='disabled')
            box.see('end')
        except Exception as e:
            print("append_chat error:", e)

    def append_system(self, text: str):
        self.append("[SYSTEM] " + text)

    def send(self, text: str):
        if not text:
            return
        self.append(f"You: {text}")
        self.app.ui.chat_entry.delete(0, 'end')
        if self.app.sock:
            try:
                send_packet(self.app.sock, TYPE_TEXT, text.encode('utf-8'))
            except Exception as e:
                print("Chat send error:", e)
                self.append_system("Failed to send chat")

    def handle_incoming(self, text: str):
        self.append(f"Peer: {text}")
