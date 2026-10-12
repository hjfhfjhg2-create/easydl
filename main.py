import os
import threading
from pathlib import Path

import yt_dlp
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle

APP_NAME = "EasyDL"

BG = (0.035, 0.055, 0.10, 1)
PANEL = (0.075, 0.105, 0.17, 1)
PANEL2 = (0.10, 0.14, 0.22, 1)
BLUE = (0.24, 0.43, 1.0, 1)
GREEN = (0.12, 0.72, 0.52, 1)
WHITE = (0.94, 0.96, 1.0, 1)
MUTED = (0.62, 0.68, 0.78, 1)


def rounded(widget, color, radius=16):
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(radius)]
        )

    def update(*_):
        shape.pos = widget.pos
        shape.size = widget.size

    widget.bind(pos=update, size=update)


def label(text, size=14, color=WHITE, height=32, bold=False):
    item = Label(
        text=text,
        font_size=sp(size),
        color=color,
        bold=bold,
        size_hint_y=None,
        height=dp(height),
        halign="left",
        valign="middle"
    )
    item.bind(
        size=lambda obj, val:
        setattr(obj, "text_size", (val[0], None))
    )
    return item


def button(text, color=BLUE, height=46):
    return Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        font_size=sp(14),
        bold=True,
        color=WHITE,
        background_normal="",
        background_down="",
        background_color=color
    )


class EasyDL(App):
    def build(self):
        self.title = "EasyDL"
        Window.clearcolor = BG

        self.mode = "video"
        self.busy = False
        self.download_log = []

        root = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10)
        )

        header = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(10)
        )

        logo = label("↓", 30, WHITE, 52, True)
        logo.size_hint_x = None
        logo.width = dp(52)
        rounded(logo, BLUE, 15)

        titlebox = BoxLayout(orientation="vertical")
        titlebox.add_widget(label("EasyDL", 24, WHITE, 34, True))
        titlebox.add_widget(
            label("SMART MEDIA DOWNLOADER", 9, MUTED, 20, True)
        )

        header.add_widget(logo)
        header.add_widget(titlebox)
        root.add_widget(header)

        root.add_widget(
            label("حمّل الفيديو أو الصوت بسهولة", 17, WHITE, 34, True)
        )

        card = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(112)
        )
        rounded(card, PANEL)

        card.add_widget(label("رابط الفيديو أو قائمة التشغيل", 12, MUTED))
        self.url_input = TextInput(
            hint_text="الصق الرابط هنا...",
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            font_size=sp(14),
            foreground_color=WHITE,
            hint_text_color=MUTED,
            background_normal="",
            background_active="",
            background_color=PANEL2,
            cursor_color=GREEN
        )
        card.add_widget(self.url_input)
        root.add_widget(card)

        root.add_widget(label("نوع التحميل", 13, WHITE, 26, True))

        choices = GridLayout(
            cols=2,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46)
        )

        self.video_btn = button("▶  فيديو MP4", BLUE)
        self.audio_btn = button("♫  صوت MP3", PANEL2)

        self.video_btn.bind(on_release=lambda *_: self.select_mode("video"))
        self.audio_btn.bind(on_release=lambda *_: self.select_mode("audio"))

        choices.add_widget(self.video_btn)
        choices.add_widget(self.audio_btn)
        root.add_widget(choices)

        root.add_widget(label("جودة الفيديو", 12, MUTED, 24, True))
        self.video_quality = Spinner(
            text="أفضل جودة",
            values=("أفضل جودة", "1080p", "720p", "480p", "360p"),
            size_hint_y=None,
            height=dp(42),
            font_size=sp(13),
            color=WHITE,
            background_normal="",
            background_color=PANEL2
        )
        root.add_widget(self.video_quality)

        root.add_widget(label("جودة الصوت", 12, MUTED, 24, True))
        self.audio_quality = Spinner(
            text="192 kbps",
            values=("320 kbps", "192 kbps", "128 kbps"),
            size_hint_y=None,
            height=dp(42),
            font_size=sp(13),
            color=WHITE,
            background_normal="",
            background_color=PANEL2
        )
        root.add_widget(self.audio_quality)

        self.start_btn = button("↓   ابدأ التحميل", BLUE, 50)
        self.start_btn.bind(on_release=self.start_download)
        root.add_widget(self.start_btn)

        status_card = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint_y=None,
            height=dp(92)
        )
        rounded(status_card, PANEL)

        self.status = label("جاهز لاستقبال الرابط", 12, WHITE)
        status_card.add_widget(self.status)

        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(8)
        )
        status_card.add_widget(self.progress)
        self.percent = label("0%", 11, GREEN, 22, True)
        status_card.add_widget(self.percent)
        root.add_widget(status_card)

        root.add_widget(label("سجل التنزيلات", 14, WHITE, 28, True))

        self.log_label = label("لم يبدأ أي تنزيل بعد.", 11, MUTED, 50)
        self.log_label.valign = "top"

        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        return root

    def select_mode(self, mode):
        self.mode = mode
        self.video_btn.background_color = (
            BLUE if mode == "video" else PANEL2
        )
        self.audio_btn.background_color = (
            BLUE if mode == "audio" else PANEL2
        )

        self.status.text = (
            "تم اختيار فيديو MP4"
            if mode == "video"
            else "تم اختيار صوت MP3"
        )

    def get_download_folder(self):
        if platform == "android":
            from android.storage import primary_external_storage_path
            folder = Path(primary_external_storage_path()) / "Download" / "EasyDL"
        else:
            folder = Path.home() / "Downloads" / "EasyDL"

        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def start_download(self, *_):
        if self.busy:
            return

        url = self.url_input.text.strip()

        if not url.startswith(("https://", "http://")):
            self.status.text = "من فضلك أدخل رابطًا صحيحًا."
            return

        self.busy = True
        self.progress.value = 0
        self.percent.text = "0%"
        self.start_btn.disabled = True
        self.status.text = "جاري تجهيز التنزيل..."

        threading.Thread(
            target=self.download_worker,
            args=(url,),
            daemon=True
        ).start()

    def download_worker(self, url):
        try:
            folder = self.get_download_folder()
            is_audio = self.mode == "audio"

            if is_audio:
                bitrate = self.audio_quality.text.split()[0]
                bitrate = bitrate if bitrate.isdigit() else "192"

                postprocessors = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate
                }]

                options = {
                    "format": "bestaudio/best",
                    "outtmpl": str(folder / "%(title)s.%(ext)s"),
                    "noplaylist": False,
                    "ignoreerrors": True,
                    "postprocessors": postprocessors,
                    "progress_hooks": [self.progress_hook],
                    "quiet": True,
                    "no_warnings": True
                }
            else:
                quality = self.video_quality.text
                heights = {
                    "1080p": 1080,
                    "720p": 720,
                    "480p": 480,
                    "360p": 360
                }

                if quality in heights:
                    height = heights[quality]
                    fmt = (
                        f"bestvideo[height<={height}]"
                        "+bestaudio/best"
                        f"[height<={height}]/best"
                    )
                else:
                    fmt = "bestvideo+bestaudio/best"

                options = {
                    "format": fmt,
                    "merge_output_format": "mp4",
                    "outtmpl": str(folder / "%(title)s.%(ext)s"),
                    "noplaylist": False,
                    "ignoreerrors": True,
                    "progress_hooks": [self.progress_hook],
                    "quiet": True,
                    "no_warnings": True
                }

            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(url, download=True)

            if not info:
                raise RuntimeError("لم يتم العثور على محتوى قابل للتنزيل.")

            Clock.schedule_once(
                lambda dt: self.finish_success(folder), 0
            )

        except Exception as exc:
            message = str(exc)[:250]
            Clock.schedule_once(
                lambda dt, msg=message: self.finish_error(msg), 0
            )

    def progress_hook(self, data):
        state = data.get("status")

        if state == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            current = data.get("downloaded_bytes", 0)

            if total:
                value = min(100, current * 100 / total)
                Clock.schedule_once(
                    lambda dt, v=value: self.update_progress(v), 0
                )

            name = os.path.basename(data.get("filename", "ملف"))
            Clock.schedule_once(
                lambda dt, n=name: self.update_status("جاري تنزيل: " + n), 0
            )

        elif state == "finished":
            Clock.schedule_once(
                lambda dt: self.update_status("جاري تجهيز الملف النهائي..."), 0
            )

    def update_progress(self, value):
        self.progress.value = value
        self.percent.text = f"{int(value)}%"

    def update_status(self, message):
        self.status.text = message

    def finish_success(self, folder):
        self.busy = False
        self.start_btn.disabled = False
        self.progress.value = 100
        self.percent.text = "اكتمل"
        self.status.text = "انتهت عملية التنزيل. تحقق من الملفات."
        self.log_label.text = (
            "مجلد التنزيل:\n" + str(folder)
            + "\n\nافتح مدير الملفات وتحقق من الملفات الموجودة."
        )

    def finish_error(self, message):
        self.busy = False
        self.start_btn.disabled = False
        self.status.text = "فشل التنزيل"
        self.log_label.text = "تفاصيل الخطأ:\n" + message


if __name__ == "__main__":
    EasyDL().run()
