import os
import threading
import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import platform
import yt_dlp


def get_folder():
    path = "/storage/emulated/0/Download/EasyDL"
    try:
        os.makedirs(path, exist_ok=True)
        t = os.path.join(path, ".t")
        open(t, "w").close()
        os.remove(t)
        return path
    except Exception:
        fb = os.path.join(App.get_running_app().user_data_dir, "downloads")
        os.makedirs(fb, exist_ok=True)
        return fb


class DL(App):
    def build(self):
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        self.url = TextInput(hint_text="Paste link here", multiline=False,
                             size_hint_y=None, height=120, font_size=18)
        root.add_widget(self.url)

        row = BoxLayout(size_hint_y=None, height=110, spacing=8)
        self.mp4 = ToggleButton(text="MP4 video", group="fmt", state="down")
        self.mp3 = ToggleButton(text="MP3 audio", group="fmt")
        row.add_widget(self.mp4)
        row.add_widget(self.mp3)
        root.add_widget(row)

        self.btn = Button(text="Download", size_hint_y=None,
                          height=130, font_size=22)
        self.btn.bind(on_release=self.start)
        root.add_widget(self.btn)

        self.bar = ProgressBar(max=100, size_hint_y=None, height=30)
        root.add_widget(self.bar)

        self.status = Label(text="Ready", size_hint_y=None, height=70)
        self.status.bind(width=lambda *a: setattr(
            self.status, "text_size", (self.status.width, None)))
        root.add_widget(self.status)

        self.log = Label(text="", size_hint_y=None, halign="left", valign="top")
        self.log.bind(
            width=lambda *a: setattr(self.log, "text_size", (self.log.width, None)),
            texture_size=lambda *a: setattr(self.log, "height", self.log.texture_size[1]),
        )
        sv = ScrollView()
        sv.add_widget(self.log)
        root.add_widget(sv)
        return root

    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                                 Permission.READ_EXTERNAL_STORAGE])

    def set_status(self, text, pct=None):
        def f(dt):
            self.status.text = text
            if pct is not None:
                self.bar.value = pct
        Clock.schedule_once(f)

    def add_log(self, msg):
        def f(dt):
            self.log.text += msg + "\n"
        Clock.schedule_once(f)

    def start(self, *a):
        url = self.url.text.strip()
        if not url:
            self.set_status("Paste a link first")
            return
        self.btn.disabled = True
        self.bar.value = 0
        threading.Thread(target=self.run, args=(url, self.mp3.state == "down"),
                         daemon=True).start()

    def hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                pct = d["downloaded_bytes"] * 100 / total
                info = d.get("info_dict", {})
                n, c = info.get("playlist_index"), info.get("n_entries")
                pre = "[%s/%s] " % (n, c) if n and c else ""
                self.set_status("%s%.0f%%  %s" % (pre, pct, d.get("_speed_str", "").strip()), pct)
        elif d["status"] == "finished":
            self.add_log("Downloaded: " + os.path.basename(d.get("filename", "")))

    def run(self, url, audio):
        try:
            folder = get_folder()
            tmpl = os.path.join(
                folder,
                "%(playlist_title&{}/|)s%(playlist_index&{} - |)s%(title).50s.%(ext)s",
            )
            opts = {
                "outtmpl": tmpl,
                "ignoreerrors": True,
                "retries": 10,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "progress_hooks": [self.hook],
            }
            if audio:
                opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
            else:
                opts["format"] = "b[ext=mp4][height<=720]/b[height<=720]/b"
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.set_status("Finished. Saved in: " + folder, 100)
        except Exception as e:
            self.set_status("Error")
            self.add_log("ERROR: " + str(e))
        finally:
            Clock.schedule_once(lambda dt: setattr(self.btn, "disabled", False))


DL().run()
