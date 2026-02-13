import os
import sys
import random
from dataclasses import dataclass
from typing import List, Optional

# nervige Qt-Logs ausblenden
os.environ.setdefault("QT_LOGGING_RULES", "qt.core.qfuture.continuations=false")

from PySide6.QtCore import Qt, QTimer, QSize, QUrl, Slot, Signal, QObject, QEvent, QRect
from PySide6.QtGui import QPalette, QColor, QPixmap, QAction, QKeySequence, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog,
    QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QMessageBox, QToolButton, QSlider, QStyle, QMenu, QWidgetAction,
    QComboBox, QSpinBox, QCheckBox, QDialog, QFrame
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink


# ---- Formate ----------------------------------------------------------------

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mpeg", ".mpg", ".m4v"}


def is_image(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


# ---- Theme ------------------------------------------------------------------

def apply_dark_palette(app: QApplication) -> None:
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(18, 18, 20))
    pal.setColor(QPalette.Base, QColor(24, 24, 28))
    pal.setColor(QPalette.AlternateBase, QColor(32, 32, 36))

    # ALLE Schrift weiß
    pal.setColor(QPalette.WindowText, QColor(255, 255, 255))
    pal.setColor(QPalette.Text, QColor(255, 255, 255))
    pal.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    try:
        pal.setColor(QPalette.PlaceholderText, QColor(200, 200, 200))
    except Exception:
        pass

    pal.setColor(QPalette.Button, QColor(28, 28, 32))
    pal.setColor(QPalette.Highlight, QColor(78, 130, 255))
    pal.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    pal.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    pal.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    app.setPalette(pal)


def apply_light_palette(app: QApplication) -> None:
    app.setPalette(app.style().standardPalette())


# ---- Datenmodell ------------------------------------------------------------

@dataclass
class MediaItem:
    path: str

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def kind(self) -> str:
        if is_image(self.path):
            return "bild"
        if is_video(self.path):
            return "video"
        return "anders"


# ---- Drag&Drop --------------------------------------------------------------

class DropBereich(QWidget):
    ordner_fallen_gelassen = Signal(str)
    dateien_fallen_gelassen = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if not urls:
            return
        folders = [p for p in urls if os.path.isdir(p)]
        if folders:
            self.ordner_fallen_gelassen.emit(folders[0])
            return
        files = [p for p in urls if os.path.isfile(p)]
        if files:
            self.dateien_fallen_gelassen.emit(files)


class DropListe(QListWidget):
    ordner_fallen_gelassen = Signal(str)
    dateien_fallen_gelassen = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if not urls:
            return
        folders = [p for p in urls if os.path.isdir(p)]
        if folders:
            self.ordner_fallen_gelassen.emit(folders[0])
            return
        files = [p for p in urls if os.path.isfile(p)]
        if files:
            self.dateien_fallen_gelassen.emit(files)


# ---- Click-to-seek Slider ---------------------------------------------------

class ClickSlider(QSlider):
    """Klick auf die Leiste -> sofort dahin springen (click-to-seek)."""
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            minv = self.minimum()
            maxv = self.maximum()
            if maxv > minv:
                x = e.position().x()
                w = max(1.0, float(self.width()))
                ratio = max(0.0, min(1.0, x / w))
                val = int(minv + ratio * (maxv - minv))
                self.setValue(val)
        super().mousePressEvent(e)


def ms_to_hms(ms: int) -> str:
    ms = max(0, int(ms))
    sec = ms // 1000
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


# ---- Video via QVideoSink (Overlay-safe) ------------------------------------

class VideoRenderWidget(QWidget):
    """
    Rendert QVideoFrame als QImage im paintEvent -> Seekbar-Overlay ist garantiert sichtbar.
    """
    hovered = Signal(bool)
    moved = Signal()

    def __init__(self, sink: QVideoSink, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._sink = sink
        self._image = None  # QImage
        self._sink.videoFrameChanged.connect(self._on_frame)
        self.setStyleSheet("background: black;")

    @Slot()
    def _on_frame(self, frame):
        try:
            img = frame.toImage()
        except Exception:
            img = None
        self._image = img if (img is not None and not img.isNull()) else None
        self.update()

    def enterEvent(self, e):
        self.hovered.emit(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hovered.emit(False)
        super().leaveEvent(e)

    def mouseMoveEvent(self, e):
        self.moved.emit()
        super().mouseMoveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.black)

        if self._image is None:
            return

        img_w = self._image.width()
        img_h = self._image.height()
        if img_w <= 0 or img_h <= 0:
            return

        dst = self.rect()
        scale = min(dst.width() / img_w, dst.height() / img_h)
        w = int(img_w * scale)
        h = int(img_h * scale)
        x = dst.x() + (dst.width() - w) // 2
        y = dst.y() + (dst.height() - h) // 2
        p.drawImage(QRect(x, y, w, h), self._image)


class SeekBarWidget(QFrame):
    hover_changed = Signal(bool)

    def __init__(self, player: QMediaPlayer, parent=None):
        super().__init__(parent)
        self.player = player
        self.setObjectName("seekOverlayEmbedded")
        self.setMouseTracking(True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        self.label_pos = QLabel("0:00")
        self.label_dur = QLabel("0:00")
        self.slider = ClickSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setSingleStep(1000)
        self.slider.setPageStep(5000)
        self.slider.setTracking(True)

        lay.addWidget(self.label_pos)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.label_dur)

        self._dragging = False
        self.slider.sliderPressed.connect(self._on_press)
        self.slider.sliderReleased.connect(self._on_release)
        self.slider.valueChanged.connect(self._on_value_changed)

        self.player.positionChanged.connect(self._on_player_pos)
        self.player.durationChanged.connect(self._on_player_dur)

        self.hide()

    def enterEvent(self, e):
        self.hover_changed.emit(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hover_changed.emit(False)
        super().leaveEvent(e)

    def _on_press(self):
        self._dragging = True

    def _on_release(self):
        self._dragging = False
        self.player.setPosition(self.slider.value())

    def _on_value_changed(self, v: int):
        if self._dragging:
            self.label_pos.setText(ms_to_hms(v))

    def _on_player_pos(self, pos: int):
        if not self._dragging:
            self.slider.blockSignals(True)
            self.slider.setValue(int(pos))
            self.slider.blockSignals(False)
            self.label_pos.setText(ms_to_hms(pos))

    def _on_player_dur(self, dur: int):
        dur = max(0, int(dur))
        self.slider.setRange(0, dur)
        self.label_dur.setText(ms_to_hms(dur))


class VideoArea(QWidget):
    """Video (QVideoSink) + Seekbar unten eingebettet."""
    def __init__(self, player: QMediaPlayer, parent=None):
        super().__init__(parent)
        self.player = player
        self.sink = QVideoSink(self)
        self.video = VideoRenderWidget(self.sink, self)
        self.seekbar = SeekBarWidget(player, self)
        self.seekbar.raise_()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.video, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_seekbar()

    def _place_seekbar(self):
        margin = 14
        h = self.seekbar.sizeHint().height()
        w = max(360, self.width() - 2 * margin)
        w = min(920, w)
        x = (self.width() - w) // 2
        y = self.height() - h - margin
        self.seekbar.setGeometry(x, y, w, h)
        self.seekbar.raise_()


# ---- Vollbildanzeige --------------------------------------------------------

class VollbildAnzeige(QDialog):
    def __init__(self, parent: QWidget, video_area_full: VideoArea, on_prev, on_next):
        super().__init__(parent)
        self._on_prev = on_prev
        self._on_next = on_next
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(False)

        self.bild_label = QLabel()
        self.bild_label.setAlignment(Qt.AlignCenter)
        self.bild_label.setStyleSheet("background: black;")
        self.bild_label.setFocusPolicy(Qt.StrongFocus)

        self.video_area = video_area_full
        self.video_area.setParent(self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.bild_label, 1)
        lay.addWidget(self.video_area, 1)

        self.bild_label.hide()
        self.video_area.hide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not (e.modifiers() & Qt.ControlModifier):
            self.parent().toggle_space_action()
            return
        if e.key() == Qt.Key_F12 or (e.key() == Qt.Key_V and (e.modifiers() & Qt.ControlModifier)):
            self.parent().toggle_vollbild()
            return
        if e.key() == Qt.Key_Left:
            self._on_prev()
            return
        if e.key() == Qt.Key_Right:
            self._on_next()
            return
        if e.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)


# ---- Hilfe-Popup ------------------------------------------------------------

class HilfePopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip)
        self.setObjectName("hilfePopup")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)

        txt = QLabel(
            "<b>Tastenkürzel</b><br>"
            "Strg+O: Ordner öffnen<br>"
            "Leertaste: Start/Pause/Weiter (auch im Vollbild)<br>"
            "Strg+S: Stopp<br>"
            "Pfeil links/rechts: Zurück/Weiter (auch im Vollbild)<br>"
            "Strg+R: Dauerschleife an/aus<br>"
            "Strg+Z: Zufall an/aus<br>"
            "Strg+V oder F12: Vollbild (nur Medium) an/aus<br>"
            "Esc: Vollbild verlassen<br><br>"
            "<b>Wissenswert</b><br>"
            "• Filter wirkt immer (auch ohne Dauerschleife / nur Zufall).<br>"
            "• Timer gilt nur für Bilder – Videos laufen komplett.<br>"
            "• Drag&Drop: Ordner/Dateien in Liste oder Anzeige ziehen.<br>"
            "• Im Video: Zeitleiste unten bei Mausbewegung (2s ohne Bewegung -> aus)."
        )
        txt.setWordWrap(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(txt)


# ---- Hauptfenster -----------------------------------------------------------

class SlideShowWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MySlide")
        self.setMinimumSize(1120, 720)

        self.current_dir: Optional[str] = None
        self.all_items: List[MediaItem] = []
        self.playlist: List[MediaItem] = []
        self.play_index: int = -1

        self.running = False
        self.paused = False
        self._bild_rest_ms: int = 0

        self.zufall_an = False
        self.repeat_an = True
        self.filter_option = "Alles"
        self.dateiname_anzeigen = True
        self.skalierung = "Einpassen"
        self.dunkelmodus = False

        # Bild-Timer
        self.bild_timer = QTimer(self)
        self.bild_timer.setSingleShot(True)
        self.bild_timer.timeout.connect(self.next_item)

        # Player
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.7)
        self.audio.setMuted(False)
        self.player.setAudioOutput(self.audio)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # Anzeige Widgets
        self.bild_label = QLabel("Datei → Ordner öffnen (Strg+O), dann Diashow mit Leertaste starten.")
        self.bild_label.setAlignment(Qt.AlignCenter)
        self.bild_label.setWordWrap(True)

        # VideoAreas (normal + vollbild)
        self.video_area = VideoArea(self.player)
        self.video_area_full = VideoArea(self.player)
        self.player.setVideoOutput(self.video_area.sink)

        self.vollbild = VollbildAnzeige(self, self.video_area_full, on_prev=self.prev_item, on_next=self.next_item)
        self.vollbild.finished.connect(self._on_vollbild_closed)

        self.overlay = QLabel("")
        self.overlay.setObjectName("overlay")
        self.overlay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Hilfe Popup
        self.hilfe_popup = HilfePopup(self)
        self.hilfe_popup.hide()

        # Seekbar Sichtbarkeit / Idle-Logik:
        # - bei Mausbewegung: anzeigen + idle timer reset
        # - nach 2s ohne Mausbewegung: ausblenden (wenn Maus nicht auf Seekbar)
        self._mouse_in_seek = False
        self._seek_idle_timer = QTimer(self)
        self._seek_idle_timer.setSingleShot(True)
        self._seek_idle_timer.timeout.connect(self._seek_hide_due_to_idle)

        # Hover/Move Signale (normal + fullscreen)
        for va in (self.video_area, self.video_area_full):
            va.video.hovered.connect(self._on_video_hover)
            va.video.moved.connect(self._on_video_move)
            va.seekbar.hover_changed.connect(self._on_seek_hover)

        self._build_menubar()
        self._build_ui()
        self._apply_styles()
        apply_light_palette(QApplication.instance())

        self.repeat_btn.setChecked(True)
        self.zufall_btn.setChecked(False)
        self.interval_spin.setValue(0)

        self._rebuild_playlist()
        self._update_status("Bereit")

        self.menuBar().installEventFilter(self)

    # ---- Menü ----------------------------------------------------------------

    def _build_menubar(self) -> None:
        mb = self.menuBar()

        m_file = mb.addMenu("Datei")
        act_open = QAction("Ordner öffnen…", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self.choose_folder)
        m_file.addAction(act_open)

        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        m_file.addSeparator()
        m_file.addAction(act_quit)

        m_set = mb.addMenu("Einstellungen")

        m_filter = m_set.addMenu("Filter")
        self._add_combo_to_menu_no_label(
            m_filter,
            items=["Alles", "Nur ausgewähltes", "Nur Bilder", "Nur Videos"],
            current=self.filter_option,
            on_change=self._set_filter,
        )

        m_view = m_set.addMenu("Anzeige")
        act_dark = QAction("Dunkelmodus", self, checkable=True)
        act_dark.setChecked(self.dunkelmodus)
        act_dark.triggered.connect(lambda on: self._set_dunkelmodus(on))
        m_view.addAction(act_dark)

        act_name = QAction("Dateiname anzeigen", self, checkable=True)
        act_name.setChecked(self.dateiname_anzeigen)
        act_name.triggered.connect(lambda on: self._set_dateiname_anzeigen(on))
        m_view.addAction(act_name)

        self._add_combo_to_menu(
            m_view,
            label="Skalierung:",
            items=["Einpassen", "Füllen (Zuschneiden)"],
            current=self.skalierung,
            on_change=self._set_skalierung,
        )

        act_fs = QAction("Vollbild (nur Medium) umschalten", self)
        act_fs.triggered.connect(self.toggle_vollbild)
        m_view.addSeparator()
        m_view.addAction(act_fs)

        self.menu_hilfe = mb.addMenu("Hilfe")

    def _add_combo_to_menu(self, menu: QMenu, label: str, items: List[str], current: str, on_change) -> None:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 6, 10, 6)
        lab = QLabel(label)
        combo = QComboBox()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        combo.currentTextChanged.connect(on_change)
        lay.addWidget(lab)
        lay.addWidget(combo, 1)

        act = QWidgetAction(menu)
        act.setDefaultWidget(w)
        menu.addAction(act)

    def _add_combo_to_menu_no_label(self, menu: QMenu, items: List[str], current: str, on_change) -> None:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 6, 10, 6)
        combo = QComboBox()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        combo.currentTextChanged.connect(on_change)
        lay.addWidget(combo, 1)

        act = QWidgetAction(menu)
        act.setDefaultWidget(w)
        menu.addAction(act)

    # ---- UI ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        # Media Buttons
        bar = QWidget()
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(0, 0, 0, 0)
        bar_l.setSpacing(10)

        def tbtn(icon: QIcon, tooltip: str, checkable=False) -> QToolButton:
            b = QToolButton()
            b.setAutoRaise(True)
            b.setIcon(icon)
            b.setIconSize(QSize(26, 26))
            b.setToolTip(tooltip)
            b.setCheckable(checkable)
            return b

        self.prev_btn = tbtn(self.style().standardIcon(QStyle.SP_MediaSkipBackward), "Zurück (Pfeil links)")
        self.play_btn = tbtn(self.style().standardIcon(QStyle.SP_MediaPlay), "Start/Pause/Weiter (Leertaste)")
        self.stop_btn = tbtn(self.style().standardIcon(QStyle.SP_MediaStop), "Stopp (Strg+S)")
        self.next_btn = tbtn(self.style().standardIcon(QStyle.SP_MediaSkipForward), "Weiter (Pfeil rechts)")

        shuffle_icon = QIcon.fromTheme("media-playlist-shuffle")
        if shuffle_icon.isNull():
            shuffle_icon = self.style().standardIcon(QStyle.SP_BrowserReload)
        repeat_icon = QIcon.fromTheme("media-playlist-repeat")
        if repeat_icon.isNull():
            repeat_icon = self.style().standardIcon(QStyle.SP_BrowserReload)

        self.zufall_btn = tbtn(shuffle_icon, "Zufall (Strg+Z)", checkable=True)
        self.repeat_btn = tbtn(repeat_icon, "Dauerschleife (Strg+R)", checkable=True)

        self.prev_btn.clicked.connect(self.prev_item)
        self.next_btn.clicked.connect(self.next_item)
        self.stop_btn.clicked.connect(self.stop_slideshow)
        self.play_btn.clicked.connect(self.toggle_space_action)
        self.zufall_btn.toggled.connect(self._toggle_zufall)
        self.repeat_btn.toggled.connect(self._toggle_repeat)

        bar_l.addStretch(1)
        bar_l.addWidget(self.prev_btn)
        bar_l.addWidget(self.play_btn)
        bar_l.addWidget(self.stop_btn)
        bar_l.addWidget(self.next_btn)
        bar_l.addSpacing(24)
        bar_l.addWidget(self.zufall_btn)
        bar_l.addWidget(self.repeat_btn)
        bar_l.addStretch(1)
        outer.addWidget(bar)

        # Lautstärke
        vol_row = QWidget()
        vol_l = QHBoxLayout(vol_row)
        vol_l.setContentsMargins(0, 0, 0, 0)
        vol_l.setSpacing(10)

        self.vol_label = QLabel("Lautstärke")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(360)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)

        self.mute_cb = QCheckBox("Stumm")
        self.mute_cb.stateChanged.connect(self._on_mute_changed)

        vol_l.addStretch(1)
        vol_l.addWidget(self.vol_label)
        vol_l.addWidget(self.vol_slider)
        vol_l.addWidget(self.mute_cb)
        vol_l.addStretch(1)
        outer.addWidget(vol_row)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(8)

        self.folder_label = QLabel("Kein Ordner gewählt (Datei → Ordner öffnen…)")
        self.folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.folder_label.setObjectName("folderLabel")

        self.listw = DropListe()
        self.listw.setSelectionMode(QListWidget.SingleSelection)
        self.listw.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.listw.itemChanged.connect(lambda _: self._rebuild_playlist())
        self.listw.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.listw.ordner_fallen_gelassen.connect(self._drop_ordner)
        self.listw.dateien_fallen_gelassen.connect(self._drop_dateien)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(0, 3600)
        self.interval_spin.setSuffix(" s")
        self.interval_spin.setToolTip("Bilder-Intervall. 0 = 10 Sekunden. Gilt NICHT für Videos.")

        left_l.addWidget(self.folder_label)
        left_l.addWidget(self.listw, 1)
        left_l.addWidget(QLabel("Bild-Intervall (Timer):"))
        left_l.addWidget(self.interval_spin)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)

        right_l.addWidget(self.overlay)

        self.drop_viewer = DropBereich()
        self.drop_viewer.ordner_fallen_gelassen.connect(self._drop_ordner)
        self.drop_viewer.dateien_fallen_gelassen.connect(self._drop_dateien)

        viewer_l = QVBoxLayout(self.drop_viewer)
        viewer_l.setContentsMargins(0, 0, 0, 0)
        viewer_l.addWidget(self.bild_label, 1)
        viewer_l.addWidget(self.video_area, 1)

        right_l.addWidget(self.drop_viewer, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 760])
        outer.addWidget(splitter, 1)

        self.status = self.statusBar()
        self.video_area.hide()

        self._setup_shortcuts()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QLabel#folderLabel { font-weight: 650; }
            QLabel#overlay {
                padding: 6px 10px;
                border-radius: 10px;
                background: rgba(0,0,0,0.10);
            }
            #seekOverlayEmbedded {
                border-radius: 12px;
                background: rgba(0,0,0,0.55);
                border: 2px solid white;
            }
            #seekOverlayEmbedded QLabel { color: white; font-weight: 600; }
            #seekOverlayEmbedded QSlider::groove:horizontal {
                height: 6px; border: 1px solid white; border-radius: 4px;
                background: rgba(255,255,255,0.18);
            }
            #seekOverlayEmbedded QSlider::sub-page:horizontal {
                background: rgba(255,255,255,0.35); border-radius: 4px;
            }
            #seekOverlayEmbedded QSlider::add-page:horizontal {
                background: rgba(255,255,255,0.10); border-radius: 4px;
            }
            #seekOverlayEmbedded QSlider::handle:horizontal {
                width: 14px; margin: -6px 0; border-radius: 7px;
                background: #ff2b2b; border: 2px solid white;
            }
            #hilfePopup { border-radius: 12px; background: rgba(40,40,46,0.98); }
            #hilfePopup QLabel { color: white; }
        """)

    def _setup_shortcuts(self) -> None:
        def add(seq: str, fn):
            a = QAction(self)
            a.setShortcut(QKeySequence(seq))
            a.triggered.connect(fn)
            self.addAction(a)

        add("Ctrl+O", self.choose_folder)
        add("Ctrl+S", self.stop_slideshow)
        add("Ctrl+R", lambda: self.repeat_btn.setChecked(not self.repeat_btn.isChecked()))
        add("Ctrl+Z", lambda: self.zufall_btn.setChecked(not self.zufall_btn.isChecked()))
        add("Ctrl+V", self.toggle_vollbild)
        add("F12", self.toggle_vollbild)

        add("Left", self.prev_item)
        add("Right", self.next_item)
        add("Escape", self._escape_vollbild)
        add("Space", self.toggle_space_action)

    # ---- Hilfe Hover Menü ----------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.menuBar():
            if event.type() == QEvent.MouseMove:
                pos = event.position().toPoint()
                act = self.menuBar().actionAt(pos)
                if act and act.menu() is self.menu_hilfe:
                    self._show_hilfe_popup()
                else:
                    self._hide_hilfe_popup()
            elif event.type() in (QEvent.Leave, QEvent.HoverLeave):
                self._hide_hilfe_popup()
        return super().eventFilter(obj, event)

    def _show_hilfe_popup(self) -> None:
        if self.hilfe_popup.isVisible():
            return
        mb = self.menuBar()
        for act in mb.actions():
            if act.menu() is self.menu_hilfe:
                rect = mb.actionGeometry(act)
                global_pos = mb.mapToGlobal(rect.bottomLeft())
                self.hilfe_popup.move(global_pos.x(), global_pos.y() + 4)
                self.hilfe_popup.adjustSize()
                self.hilfe_popup.show()
                break

    def _hide_hilfe_popup(self) -> None:
        if self.hilfe_popup.isVisible():
            self.hilfe_popup.hide()

    # ---- Seekbar: 2s nach letzter Mausbewegung ------------------------------

    def _active_video_area(self) -> VideoArea:
        return self.video_area_full if self.vollbild.isVisible() else self.video_area

    def _active_seekbar(self) -> SeekBarWidget:
        return self._active_video_area().seekbar

    def _seek_show_if_video(self):
        if self._current_kind() == "video" and self.player.source().isValid():
            sb = self._active_seekbar()
            sb.show()
            sb.raise_()

    def _restart_seek_idle(self):
        # 2 Sekunden ohne Mausbewegung -> ausblenden (außer Mouse ist auf Seekbar)
        self._seek_idle_timer.start(2000)

    def _seek_hide_due_to_idle(self):
        if self._mouse_in_seek:
            return
        self._active_seekbar().hide()

    @Slot(bool)
    def _on_video_hover(self, on: bool):
        if on:
            self._seek_show_if_video()
            if not self._mouse_in_seek:
                self._restart_seek_idle()
        else:
            if not self._mouse_in_seek:
                self._restart_seek_idle()

    @Slot()
    def _on_video_move(self):
        self._seek_show_if_video()
        if not self._mouse_in_seek:
            self._restart_seek_idle()

    @Slot(bool)
    def _on_seek_hover(self, on: bool):
        self._mouse_in_seek = on
        if on:
            self._seek_idle_timer.stop()
            self._seek_show_if_video()
        else:
            self._restart_seek_idle()

    # ---- Einstellungen -------------------------------------------------------

    def _set_filter(self, text: str) -> None:
        self.filter_option = text
        self._rebuild_playlist()
        self._update_status("Filter geändert")

    def _set_dunkelmodus(self, on: bool) -> None:
        self.dunkelmodus = on
        app = QApplication.instance()
        if on:
            apply_dark_palette(app)
        else:
            apply_light_palette(app)

    def _set_dateiname_anzeigen(self, on: bool) -> None:
        self.dateiname_anzeigen = on
        self._refresh_overlay()

    def _set_skalierung(self, text: str) -> None:
        self.skalierung = text
        self._rescale_current()

    # ---- Vollbild ------------------------------------------------------------

    @Slot()
    def toggle_vollbild(self) -> None:
        if self.vollbild.isVisible():
            self._leave_vollbild()
        else:
            self._enter_vollbild()

    def _enter_vollbild(self) -> None:
        pos = self.player.position()
        st = self.player.playbackState()
        was_playing = (st == QMediaPlayer.PlayingState)

        self.vollbild.showFullScreen()
        self.vollbild.raise_()
        self.vollbild.setFocus()

        # Inhalt im Vollbild anzeigen
        self._render_current(autoplay=(self.running and not self.paused))

        if self._current_kind() == "video" and self.player.source().isValid():
            self.player.setVideoOutput(self.video_area_full.sink)
            self.player.setPosition(pos)
            if was_playing and self.running and not self.paused:
                self.player.play()
            else:
                self.player.pause()

    def _leave_vollbild(self) -> None:
        if not self.vollbild.isVisible():
            return
        pos = self.player.position()
        st = self.player.playbackState()
        was_playing = (st == QMediaPlayer.PlayingState)

        self.vollbild.close()

        if self._current_kind() == "video" and self.player.source().isValid():
            self.player.setVideoOutput(self.video_area.sink)
            self.player.setPosition(pos)
            if was_playing and self.running and not self.paused:
                self.player.play()
            else:
                self.player.pause()

    @Slot()
    def _on_vollbild_closed(self) -> None:
        if self._current_kind() == "video" and self.player.source().isValid():
            pos = self.player.position()
            st = self.player.playbackState()
            self.player.setVideoOutput(self.video_area.sink)
            self.player.setPosition(pos)
            if st == QMediaPlayer.PlayingState and self.running and not self.paused:
                self.player.play()
        self._active_seekbar().hide()

    @Slot()
    def _escape_vollbild(self) -> None:
        if self.vollbild.isVisible():
            self._leave_vollbild()

    # ---- Space Toggle --------------------------------------------------------

    @Slot()
    def toggle_space_action(self) -> None:
        if not self.current_dir:
            self.choose_folder()
            return

        if not self.playlist:
            self._rebuild_playlist()
            if not self.playlist:
                return

        if not self.running:
            self.running = True
            self.paused = False
            self._render_current(autoplay=True)
            self._update_play_icon()
            self._update_status("Wiedergabe")
            return

        if not self.paused:
            self._pause_everything()
            self._update_play_icon()
            self._update_status("Pause")
        else:
            self._resume_everything()
            self._update_play_icon()
            self._update_status("Wiedergabe")

    def _pause_everything(self) -> None:
        self.paused = True
        if self._current_kind() == "bild":
            self._bild_rest_ms = max(0, int(self.bild_timer.remainingTime())) if self.bild_timer.isActive() else self._interval_ms()
            self.bild_timer.stop()
        if self._current_kind() == "video" and self.player.source().isValid():
            self.player.pause()

    def _resume_everything(self) -> None:
        self.paused = False
        if self._current_kind() == "bild":
            rest = self._bild_rest_ms if self._bild_rest_ms > 0 else self._interval_ms()
            self.bild_timer.start(rest)
        if self._current_kind() == "video" and self.player.source().isValid():
            self.player.play()

    def _update_play_icon(self) -> None:
        if not self.running or self.paused:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    # ---- Stop ----------------------------------------------------------------

    @Slot()
    def stop_slideshow(self) -> None:
        self.running = False
        self.paused = False
        self._bild_rest_ms = 0
        self.bild_timer.stop()
        self.player.stop()
        self._seek_idle_timer.stop()
        self._active_seekbar().hide()
        self._update_play_icon()
        self._update_status("Gestoppt")

    # ---- Navigation ----------------------------------------------------------

    @Slot()
    def next_item(self) -> None:
        if not self.playlist:
            return
        self.bild_timer.stop()
        self.player.stop()
        self._active_seekbar().hide()

        self.play_index = 0 if self.play_index < 0 else self.play_index + 1
        if self.play_index >= len(self.playlist):
            if self.repeat_an:
                self.play_index = 0
            else:
                self.running = False
                self.paused = False
                self._update_play_icon()
                self._update_status("Ende erreicht")
                return

        self._render_current(autoplay=(self.running and not self.paused))
        self._update_play_icon()

    @Slot()
    def prev_item(self) -> None:
        if not self.playlist:
            return
        self.bild_timer.stop()
        self.player.stop()
        self._active_seekbar().hide()

        self.play_index = 0 if self.play_index < 0 else self.play_index - 1
        if self.play_index < 0:
            self.play_index = (len(self.playlist) - 1) if self.repeat_an else 0

        self._render_current(autoplay=(self.running and not self.paused))
        self._update_play_icon()

    # ---- Doppelklick ---------------------------------------------------------

    @Slot(QListWidgetItem)
    def _on_item_double_clicked(self, it: QListWidgetItem) -> None:
        path = it.data(Qt.UserRole)
        if not path:
            return
        self._rebuild_playlist()
        for idx, m in enumerate(self.playlist):
            if m.path == path:
                self.play_index = idx
                break
        else:
            self.play_index = 0

        self.running = True
        self.paused = False
        self._render_current(autoplay=True)
        self._update_play_icon()
        self._update_status("Wiedergabe")

    # ---- Drag&Drop -----------------------------------------------------------

    @Slot(str)
    def _drop_ordner(self, folder: str) -> None:
        self.current_dir = folder
        self.folder_label.setText(folder)
        self._load_folder(folder)

    @Slot(list)
    def _drop_dateien(self, files: list) -> None:
        if not files:
            return
        first = files[0]
        folder = os.path.dirname(first)
        self.current_dir = folder
        self.folder_label.setText(folder)
        self._load_folder(folder)

        wanted = set(os.path.abspath(p) for p in files)
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            p = os.path.abspath(it.data(Qt.UserRole))
            if p in wanted:
                self.listw.setCurrentRow(i)
                it.setCheckState(Qt.Checked)

    # ---- Ordner/Laden --------------------------------------------------------

    @Slot()
    def choose_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Quellordner auswählen", self.current_dir or os.path.expanduser("~"))
        if not d:
            return
        self.current_dir = d
        self.folder_label.setText(d)
        self._load_folder(d)

    def _load_folder(self, folder: str) -> None:
        self.stop_slideshow()
        self.all_items.clear()
        self.listw.blockSignals(True)
        self.listw.clear()

        try:
            for name in sorted(os.listdir(folder), key=lambda s: s.lower()):
                path = os.path.join(folder, name)
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(path)[1].lower()
                if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                    self.all_items.append(MediaItem(path))
        except Exception as e:
            self.listw.blockSignals(False)
            QMessageBox.critical(self, "Fehler", f"Ordner konnte nicht gelesen werden:\n{e}")
            return

        for item in self.all_items:
            it = QListWidgetItem(item.name)
            it.setData(Qt.UserRole, item.path)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            self.listw.addItem(it)

        if self.listw.count() > 0:
            self.listw.setCurrentRow(0)

        self.listw.blockSignals(False)
        self._rebuild_playlist()
        self._render_current(autoplay=False)
        self._update_play_icon()
        self._update_status("Ordner geladen")

    def _selected_paths(self) -> List[str]:
        paths = []
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            if it.checkState() == Qt.Checked:
                paths.append(it.data(Qt.UserRole))
        return paths

    # ---- Playlist ------------------------------------------------------------

    def _apply_filter(self, items: List[MediaItem]) -> List[MediaItem]:
        scope = self.filter_option
        if scope == "Alles":
            return items
        if scope == "Nur ausgewähltes":
            chosen = set(self._selected_paths())
            return [m for m in items if m.path in chosen]
        if scope == "Nur Bilder":
            return [m for m in items if m.kind == "bild"]
        if scope == "Nur Videos":
            return [m for m in items if m.kind == "video"]
        return items

    def _rebuild_playlist(self) -> None:
        items = self._apply_filter(list(self.all_items))
        if self.zufall_an:
            rnd = random.Random()
            rnd.seed((self.current_dir or "") + str(len(items)))
            rnd.shuffle(items)

        current_path = None
        if 0 <= self.play_index < len(self.playlist):
            current_path = self.playlist[self.play_index].path

        self.playlist = items
        if current_path:
            for idx, m in enumerate(self.playlist):
                if m.path == current_path:
                    self.play_index = idx
                    break
            else:
                self.play_index = 0 if self.playlist else -1
        else:
            self.play_index = 0 if self.playlist else -1

    # ---- Vorschau ------------------------------------------------------------

    @Slot()
    def _on_list_selection_changed(self) -> None:
        items = self.listw.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        item = MediaItem(path)

        self.running = False
        self.paused = False
        self._bild_rest_ms = 0
        self.bild_timer.stop()
        self.player.stop()
        self._seek_idle_timer.stop()
        self._active_seekbar().hide()
        self._update_play_icon()

        self._refresh_overlay(item)
        self._render_item(item, autoplay=False)
        self._update_status("Vorschau")

    # ---- Render --------------------------------------------------------------

    def _current_kind(self) -> str:
        if 0 <= self.play_index < len(self.playlist):
            return self.playlist[self.play_index].kind
        return "anders"

    def _interval_ms(self) -> int:
        sec = int(self.interval_spin.value())
        return (10 if sec <= 0 else sec) * 1000

    def _render_current(self, autoplay: bool) -> None:
        if 0 <= self.play_index < len(self.playlist):
            self._render_item(self.playlist[self.play_index], autoplay=autoplay)

    def _render_item(self, item: MediaItem, autoplay: bool) -> None:
        self._refresh_overlay(item)
        self._active_seekbar().hide()

        if item.kind == "bild":
            self.player.stop()
            self.video_area.hide()
            self.bild_label.show()

            if self.vollbild.isVisible():
                self.video_area_full.hide()
                self.vollbild.video_area.hide()
                self.vollbild.bild_label.show()

            pix = QPixmap(item.path)
            if pix.isNull():
                lbl = self.vollbild.bild_label if self.vollbild.isVisible() else self.bild_label
                lbl.setText(f"Konnte Bild nicht laden:\n{item.name}")
                return

            lbl = self.vollbild.bild_label if self.vollbild.isVisible() else self.bild_label
            QTimer.singleShot(0, lambda: self._set_pixmap_scaled(lbl, pix))

            self.bild_timer.stop()
            if autoplay:
                self._bild_rest_ms = self._interval_ms()
                self.bild_timer.start(self._bild_rest_ms)
            return

        if item.kind == "video":
            self.bild_timer.stop()

            # Videobereich sichtbar (normal oder vollbild)
            if self.vollbild.isVisible():
                self.vollbild.bild_label.hide()
                self.vollbild.video_area.show()
                self.player.setVideoOutput(self.video_area_full.sink)
            else:
                self.bild_label.hide()
                self.video_area.show()
                self.player.setVideoOutput(self.video_area.sink)

            # Quelle nur setzen, wenn anderes Video (kein Neustart)
            current = self.player.source().toLocalFile() if self.player.source().isValid() else ""
            if os.path.abspath(current) != os.path.abspath(item.path):
                self.player.setSource(QUrl.fromLocalFile(item.path))

            if autoplay:
                self.player.play()
            else:
                self.player.pause()
            return

        # sonst
        self.bild_timer.stop()
        self.player.stop()
        self.video_area.hide()
        self.bild_label.show()
        self.bild_label.setText(f"Nicht unterstützter Typ:\n{item.name}")

    def _set_pixmap_scaled(self, target_label: QLabel, pix: QPixmap) -> None:
        target = target_label.size()
        if target.width() <= 1 or target.height() <= 1:
            return
        if self.skalierung == "Füllen (Zuschneiden)":
            scaled = pix.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        else:
            scaled = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        target_label.setPixmap(scaled)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._rescale_current()

    def _rescale_current(self) -> None:
        if 0 <= self.play_index < len(self.playlist):
            item = self.playlist[self.play_index]
            if item.kind == "bild":
                pix = QPixmap(item.path)
                if not pix.isNull():
                    lbl = self.vollbild.bild_label if self.vollbild.isVisible() else self.bild_label
                    QTimer.singleShot(0, lambda: self._set_pixmap_scaled(lbl, pix))

    def _refresh_overlay(self, item: Optional[MediaItem] = None) -> None:
        if not self.dateiname_anzeigen:
            self.overlay.setText("")
            return
        self.overlay.setText(item.name if item else "")

    # ---- Buttons / Settings --------------------------------------------------

    @Slot()
    def _toggle_zufall(self, on: bool) -> None:
        self.zufall_an = on
        self._rebuild_playlist()
        self._update_status("Zufall geändert")

    @Slot()
    def _toggle_repeat(self, on: bool) -> None:
        self.repeat_an = on
        self._update_status("Dauerschleife geändert")

    @Slot()
    def _on_volume_changed(self, v: int) -> None:
        self.audio.setVolume(max(0.0, min(1.0, v / 100.0)))

    @Slot()
    def _on_mute_changed(self) -> None:
        self.audio.setMuted(self.mute_cb.isChecked())
        self._update_status("Ton geändert")

    # ---- Multimedia ----------------------------------------------------------

    @Slot()
    def _on_player_error(self, error, error_string: str) -> None:
        if error_string:
            self.status.showMessage(f"Video-Fehler: {error_string}")

    @Slot()
    def _on_media_status_changed(self, status) -> None:
        if not self.running or self.paused:
            return
        if status == QMediaPlayer.EndOfMedia:
            self.next_item()

    # ---- Status --------------------------------------------------------------

    def _update_status(self, prefix="") -> None:
        prefix = "" if prefix is None else str(prefix)
        total = len(self.playlist)
        idx = self.play_index + 1 if self.play_index >= 0 else 0
        interval = int(self.interval_spin.value()) or 10
        modus = "Zufall" if self.zufall_an else "Reihe nach"
        rep = "an" if self.repeat_an else "aus"
        ton = "stumm" if self.mute_cb.isChecked() else "an"
        run = "läuft" if self.running else "steht"
        pau = "pausiert" if self.paused else "aktiv"
        msg = (
            f"{(prefix + '  ') if prefix else ''}"
            f"Status: {run}/{pau} | Playlist: {idx}/{total} | Modus: {modus} | "
            f"Filter: {self.filter_option} | Bild-Timer: {interval}s | Dauerschleife: {rep} | Ton: {ton}"
        )
        self.status.showMessage(msg)


# ---- Start ------------------------------------------------------------------

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MintSlide")
    app.setOrganizationName("Local")

    w = SlideShowWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
