import os
import re
import threading
import shutil
import tempfile
import traceback
from pathlib import Path

import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
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
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
import yt_dlp

import arabic_reshaper
from bidi.algorithm import get_display

# ---------------------------------------------------------------------------
# الخط العربي: بنسجّل خط عربي باسم "Roboto" (الاسم الافتراضي في Kivy)
# عشان كل العناصر (Label / Button / TextInput / Spinner) تستخدمه تلقائيًا.
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def register_arabic_font():
    regular = _first_existing([
        os.path.join(APP_DIR, "fonts", "Cairo-Regular.ttf"),
        os.path.join(APP_DIR, "fonts", "Tajawal-Regular.ttf"),
        "/system/fonts/NotoNaskhArabic-Regular.ttf",
        "/system/fonts/NotoSansArabic-Regular.ttf",
        "/system/fonts/NotoSansArabicUI-Regular.ttf",
        "/system/fonts/DroidSansArabic.ttf",
    ])
    bold = _first_existing([
        os.path.join(APP_DIR, "fonts", "Cairo-Bold.ttf"),
        os.path.join(APP_DIR, "fonts", "Tajawal-Bold.ttf"),
        "/system/fonts/NotoNaskhArabic-Bold.ttf",
        "/system/fonts/NotoSansArabic-Bold.ttf",
        "/system/fonts/NotoSansArabicUI-Bold.ttf",
    ]) or regular
    if regular:
        LabelBase.register(name="Roboto", fn_regular=regular, fn_bold=bold,
                           fn_italic=regular, fn_bolditalic=bold)
    else:
        print("EasyDL: لم يتم العثور على خط عربي — حط Cairo-Regular.ttf في فولدر fonts")


register_arabic_font()

NL = chr(10)  # سطر جديد (من غير backslash عشان النسخ ما يكسرهوش)
_AR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def has_ar(text):
    return bool(text) and bool(_AR_RE.search(text))


def ar(text):
    """يشبّك الحروف العربية ويظبط الاتجاه عشان Kivy يعرضها صح."""
    if not text or not has_ar(text):
        return text
    try:
        return NL.join(get_display(arabic_reshaper.reshape(line)) for line in text.split(NL))
    except Exception:
        return text


APP_NAME = "EasyDL"
BG = (0.035, 0.055, 0.10, 1)
PANEL = (0.075, 0.105, 0.17, 1)
PANEL_2 = (0.10, 0.14, 0.22, 1)
BLUE = (0.24, 0.43, 1.0, 1)
CYAN = (0.20, 0.82, 0.75, 1)
WHITE = (0.94, 0.96, 1.0, 1)
MUTED = (0.62, 0.68, 0.78, 1)
RED = (1.0, 0.35, 0.39, 1)

# نصوص عربية بنقارن بيها في الكود
Q_BEST = ar("أفضل جودة")
AUDIO_ORIGINAL = ar("الصوت الأصلي")
LOG_EMPTY = "لم يبدأ أي تنزيل بعد."


def rounded_bg(widget, color, radius=16):
    with widget.canvas.before:
        Color(*color)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    def update(*_):
        rect.pos = widget.pos
        rect.size = widget.size
    widget.bind(pos=update, size=update)
    return widget


def make_label(text, size=14, color=WHITE, bold=False, height=None, halign=None):
    if halign is None:
        halign = "right" if has_ar(text) else "left"
    w = Label(text=ar(text), font_size=sp(size), color=color, bold=bold,
              halign=halign, valign="middle", size_hint_y=None,
              height=dp(height or max(28, size * 2.0)))
    w.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
    return w


def make_button(text, color=BLUE, height=48):
    b = Button(text=ar(text), size_hint_y=None, height=dp(height), font_size=sp(14),
               bold=True, color=WHITE, background_normal="", background_down="",
               background_color=color)
    return b


class EasyDL(App):
    def build(self):
        self.title = "EasyDL - Smart Downloader"
        Window.clearcolor = BG
        self.busy = False
        self.success_count = 0
        self.failure_count = 0
        self.downloaded_paths = []
        self.current_playlist_total = None
        self.log_lines = []

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        header = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(10))
        logo = Label(text="DL", font_size=sp(22), bold=True, color=WHITE,
                     size_hint_x=None, width=dp(54))
        rounded_bg(logo, BLUE, 15)
        title_col = BoxLayout(orientation="vertical", spacing=0)
        title_col.add_widget(make_label("EasyDL", 23, WHITE, True, 34, "left"))
        title_col.add_widget(make_label("SMART MEDIA DOWNLOADER", 9, MUTED, True, 20, "left"))
        header.add_widget(logo)
        header.add_widget(title_col)
        header.add_widget(Widget())
        root.add_widget(header)

        root.add_widget(make_label("حمّل الفيديو أو الصوت بسهولة", 17, WHITE, True, 32))
        link_card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8),
                              size_hint_y=None, height=dp(116))
        rounded_bg(link_card, PANEL, 18)
        link_card.add_widget(make_label("رابط الفيديو أو Playlist", 12, MUTED, True, 24))
        self.url_input = TextInput(hint_text=ar("الصق الرابط هنا..."), multiline=False,
                                   size_hint_y=None, height=dp(48), font_size=sp(14),
                                   padding=[dp(12), dp(12), dp(12), dp(10)],
                                   foreground_color=WHITE, hint_text_color=MUTED,
                                   background_normal="", background_active="",
                                   background_color=PANEL_2, cursor_color=CYAN)
        link_card.add_widget(self.url_input)
        root.add_widget(link_card)

        root.add_widget(make_label("نوع الملف", 13, WHITE, True, 26))
        formats = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(48))
        self.video_btn = make_button("فيديو", BLUE, 48)
        self.audio_btn = make_button("صوت", PANEL_2, 48)
        self.video_btn.bind(on_release=lambda *_: self.select_mode("video"))
        self.audio_btn.bind(on_release=lambda *_: self.select_mode("audio"))
        self.mode = "video"
        formats.add_widget(self.video_btn)
        formats.add_widget(self.audio_btn)
        root.add_widget(formats)

        quality_row = BoxLayout(size_hint_y=None, height=dp(68), spacing=dp(10))
        quality_col = BoxLayout(orientation="vertical", spacing=dp(3))
        quality_col.add_widget(make_label("الجودة", 12, MUTED, True, 22))
        self.quality = Spinner(text=Q_BEST, values=(Q_BEST, "1080p", "720p", "480p", "360p"),
                               size_hint_y=None, height=dp(40), font_size=sp(13),
                               color=WHITE, background_normal="", background_color=PANEL_2)
        quality_col.add_widget(self.quality)
        self.audio_quality = Spinner(text="MP3 · 192 kbps",
                                     values=("MP3 · 320 kbps", "MP3 · 192 kbps", "MP3 · 128 kbps", AUDIO_ORIGINAL),
                                     size_hint_y=None, height=dp(40), font_size=sp(12),
                                     color=WHITE, background_normal="", background_color=PANEL_2)
        self.audio_quality.opacity = 0
        self.audio_quality.disabled = True
        quality_row.add_widget(quality_col)
        root.add_widget(quality_row)
        root.add_widget(self.audio_quality)

        self.download_btn = make_button("ابدأ التحميل", BLUE, 52)
        self.download_btn.bind(on_release=self.start_download)
        root.add_widget(self.download_btn)

        progress_card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8),
                                  size_hint_y=None, height=dp(102))
        rounded_bg(progress_card, PANEL, 18)
        status_head = BoxLayout(size_hint_y=None, height=dp(25))
        status_head.add_widget(make_label("حالة التحميل", 12, MUTED, True, 24))
        self.percent_label = make_label("0%", 12, CYAN, True, 24, "left")
        status_head.add_widget(self.percent_label)
        progress_card.add_widget(status_head)
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(8))
        progress_card.add_widget(self.progress)
        self.status = make_label("جاهز لاستقبال الرابط", 12, WHITE, False, 26, "right")
        progress_card.add_widget(self.status)
        root.add_widget(progress_card)

        root.add_widget(make_label("سجل التنزيلات", 14, WHITE, True, 28))
        self.log_label = make_label(LOG_EMPTY, 11, MUTED, False, 40, "right")
        self.log_label.valign = "top"
        self.log_label.bind(texture_size=lambda inst, ts: setattr(inst, "height", max(dp(40), ts[1] + dp(8))))
        self.log_box = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(12))
        self.log_box.bind(minimum_height=self.log_box.setter("height"))
        rounded_bg(self.log_box, PANEL, 16)
        self.log_box.add_widget(self.log_label)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.log_box)
        root.add_widget(scroll)

        footer = make_label("تُحفظ الملفات المكتملة في Download/EasyDL متى سمح أندرويد بذلك.", 9, MUTED, False, 24, "center")
        root.add_widget(footer)
        self.select_mode("video")
        return root

    def select_mode(self, mode):
        self.mode = mode
        video = mode == "video"
        self.video_btn.background_color = BLUE if video else PANEL_2
        self.audio_btn.background_color = PANEL_2 if video else BLUE
        self.quality.disabled = not video
        self.quality.opacity = 1 if video else 0
        self.audio_quality.disabled = video
        self.audio_quality.opacity = 0 if video else 1

    def ui(self, fn, *args):
        Clock.schedule_once(lambda _dt: fn(*args), 0)

    def set_status(self, text, pct=None):
        shown = ar(text)
        def update(_dt):
            self.status.text = shown
            if pct is not None:
                self.progress.value = max(0, min(100, pct))
                self.percent_label.text = f"{int(pct)}%"
        Clock.schedule_once(update, 0)

    def add_log(self, text):
        shown = ar(text)
        def update(_dt):
            self.log_lines.append(shown)
            self.log_label.text = NL.join(self.log_lines)
        Clock.schedule_once(update, 0)

    def start_download(self, *_):
        url = self.url_input.text.strip()
        if not url:
            self.set_status("الصق رابطًا أولًا")
            return
        if self.busy:
            return
        if not (url.startswith("https://") or url.startswith("http://")):
            self.set_status("الرابط غير صحيح - استخدم رابطًا يبدأ بـ http أو https")
            return
        self.busy = True
        self.success_count = 0
        self.failure_count = 0
        self.downloaded_paths = []
        self.download_btn.disabled = True
        self.progress.value = 0
        self.percent_label.text = "0%"
        mode = self.mode
        video_quality = self.quality.text
        audio_quality = self.audio_quality.text
        threading.Thread(target=self.download_worker,
                         args=(url, mode, video_quality, audio_quality), daemon=True).start()

    def output_folder(self):
        # Download to app-private temporary storage first; then publish to Android Downloads.
        if platform == "android":
            folder = os.path.join(self.user_data_dir, "EasyDL_temp")
        else:
            folder = os.path.join(str(Path.home()), "Downloads", "EasyDL")
        os.makedirs(folder, exist_ok=True)
        return folder

    def publish_android_download(self, source_path):
        if platform != "android":
            target_dir = os.path.join(str(Path.home()), "Downloads", "EasyDL")
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, os.path.basename(source_path))
            if os.path.abspath(source_path) != os.path.abspath(target):
                shutil.copy2(source_path, target)
            return target
        # Android 10+: use MediaStore so the result appears in the public Downloads collection.
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        MediaStore = autoclass('android.provider.MediaStore')
        ContentValues = autoclass('android.content.ContentValues')
        BuildVersion = autoclass('android.os.Build$VERSION')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        values = ContentValues()
        filename = os.path.basename(source_path)
        ext = os.path.splitext(filename)[1].lower()
        mime = 'audio/mpeg' if ext == '.mp3' else ('video/mp4' if ext == '.mp4' else 'application/octet-stream')
        values.put('_display_name', filename)
        values.put('mime_type', mime)
        if int(BuildVersion.SDK_INT) >= 29:
            values.put('relative_path', 'Download/EasyDL')
            values.put('is_pending', 1)
        uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            raise RuntimeError('أندرويد لم يسمح بحفظ الملف في مجلد التنزيلات')
        output_stream = resolver.openOutputStream(uri)
        try:
            with open(source_path, 'rb') as src:
                while True:
                    chunk = src.read(64 * 1024)
                    if not chunk:
                        break
                    output_stream.write(bytearray(chunk))
            output_stream.flush()
        finally:
            output_stream.close()
        if int(BuildVersion.SDK_INT) >= 29:
            done = ContentValues()
            done.put('is_pending', 0)
            resolver.update(uri, done, None, None)
        return f"Download/EasyDL/{filename}"

    def find_ffmpeg_dir(self):
        """Return a folder containing an executable named 'ffmpeg', or None."""
        if platform != "android":
            exe = shutil.which("ffmpeg")
            return os.path.dirname(exe) if exe else None
        try:
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            lib = os.path.join(activity.getApplicationInfo().nativeLibraryDir, "libffmpeg.so")
            if not os.path.exists(lib):
                return None
            bindir = os.path.join(self.user_data_dir, "bin")
            os.makedirs(bindir, exist_ok=True)
            link = os.path.join(bindir, "ffmpeg")
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(lib, link)
            return bindir
        except Exception:
            return None

    def progress_hook(self, data):
        if data.get('status') == 'downloading':
            total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
            downloaded = data.get('downloaded_bytes') or 0
            pct = (downloaded * 100 / total) if total else 0
            info = data.get('info_dict') or {}
            idx, total_entries = info.get('playlist_index'), info.get('n_entries')
            prefix = f"عنصر {idx}/{total_entries} · " if idx and total_entries else ""
            speed = (data.get('_speed_str') or '').strip()
            self.set_status(f"{prefix}جارٍ التحميل... {speed}", pct)
        elif data.get('status') == 'finished':
            filename = data.get('filename')
            if filename:
                self.downloaded_paths.append(filename)
            self.set_status("اكتمل تنزيل أحد الملفات...", 100)

    def download_worker(self, url, mode, video_quality, audio_quality):
        folder = self.output_folder()
        before = {}
        for base, _, names in os.walk(folder):
            for name in names:
                p = os.path.join(base, name)
                try:
                    before[p] = os.path.getmtime(p)
                except OSError:
                    pass
        template = os.path.join(folder, '%(playlist_title|Playlist)s/%(playlist_index|0)03d - %(title).180B.%(ext)s')
        # yt-dlp may not support every site or every playlist entry; don't fabricate success.
        opts = {
            'outtmpl': template,
            'noplaylist': False,
            'ignoreerrors': True,
            'retries': 5,
            'fragment_retries': 5,
            'quiet': True,
            'no_warnings': False,
            'progress_hooks': [self.progress_hook],
            'windowsfilenames': False,
            'overwrites': False,
            'continuedl': True,
        }
        ff_dir = self.find_ffmpeg_dir()
        if ff_dir:
            opts['ffmpeg_location'] = ff_dir
        if mode == 'video':
            height = {'1080p': 1080, '720p': 720, '480p': 480, '360p': 360}.get(video_quality)
            if ff_dir:
                # FFmpeg available: allow separate video+audio and merge them into mp4.
                if height:
                    opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[height<={height}]/best'
                else:
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                opts['merge_output_format'] = 'mp4'
            elif height:
                opts['format'] = f'best[height<={height}][ext=mp4]/best[height<={height}]/best'
            else:
                opts['format'] = 'best[ext=mp4]/best'
        else:
            if audio_quality == AUDIO_ORIGINAL:
                opts['format'] = 'bestaudio/best'
            else:
                if not ff_dir:
                    self.set_status('تحويل MP3 يحتاج FFmpeg مدمجًا مع نسخة أندرويد')
                    self.add_log('لم يبدأ التحميل: نسخة APK الحالية لا تحتوي على برنامج FFmpeg اللازم لتحويل الصوت إلى MP3. استخدم الصوت الأصلي مؤقتًا أو أضف FFmpeg Android إلى البناء.')
                    self.finish_worker()
                    return
                bitrate = {'MP3 · 320 kbps': '320', 'MP3 · 192 kbps': '192', 'MP3 · 128 kbps': '128'}.get(audio_quality, '192')
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}]
        try:
            self.set_status('جارٍ تحليل الرابط...', 0)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise RuntimeError('تعذر قراءة الرابط')
                if info.get('_type') == 'playlist' or info.get('entries') is not None:
                    entries = info.get('entries') or []
                    self.current_playlist_total = len(entries)
                    self.set_status(f'تم العثور على قائمة تضم {len(entries)} عنصرًا - جارٍ التنزيل', 0)
                    self.add_log(f'قائمة تشغيل: {info.get("title") or "بدون عنوان"} · {len(entries)} عنصرًا')
                else:
                    self.set_status('تم تحليل الرابط - جارٍ التنزيل', 0)
                ydl.download([url])
            # Only count non-empty completed output files.
            candidates = []
            for base, _, files in os.walk(folder):
                for name in files:
                    p = os.path.join(base, name)
                    if os.path.isfile(p) and os.path.getsize(p) > 0 and not name.endswith(('.part', '.ytdl')):
                        try:
                            if p not in before or os.path.getmtime(p) > before[p]:
                                candidates.append(p)
                        except OSError:
                            pass
            published = []
            for path in candidates:
                try:
                    target = self.publish_android_download(path)
                    published.append(target)
                except Exception as ex:
                    self.add_log(f'تعذر إظهار الملف في Downloads: {os.path.basename(path)} - {ex}')
            if published:
                self.success_count = len(published)
                self.set_status(f'اكتمل التحميل: {self.success_count} ملف', 100)
                for item in published:
                    self.add_log('تم: ' + item)
            else:
                self.set_status('لم يكتمل أي ملف', 0)
                self.add_log('لم يتم العثور على ملفات مكتملة. قد يكون الموقع غير مدعوم أو الرابط محميًا.')
        except Exception as exc:
            self.set_status('فشل التحميل')
            self.add_log('خطأ: ' + str(exc))
        finally:
            self.finish_worker()

    def finish_worker(self):
        def done(_dt):
            self.busy = False
            self.download_btn.disabled = False
        Clock.schedule_once(done, 0)


if __name__ == '__main__':
    EasyDL().run()
