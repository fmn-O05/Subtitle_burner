import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QFileDialog, QWidget,
                            QProgressBar, QComboBox, QColorDialog, QSpinBox,
                            QGroupBox, QFormLayout, QMessageBox, QSlider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir
from PyQt5.QtGui import QColor, QFont, QIcon

class SubtitleBurnerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, video_path, subtitle_path, output_path, font_size, 
                font_name, font_color, position, outline_width):
        super().__init__()
        self.video_path = video_path
        self.subtitle_path = subtitle_path
        self.output_path = output_path
        self.font_size = font_size
        self.font_name = font_name
        self.font_color = font_color
        self.position = position
        self.outline_width = outline_width
        
    def run(self):
        try:
            # Get video duration to calculate progress
            duration_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', self.video_path
            ]
            duration = float(subprocess.check_output(duration_cmd).decode().strip())
            
            # Build FFmpeg command
            # Position mappings: 0=bottom, 1=top, 2=middle
            position_map = {
                0: "subtitles='{}':force_style='Fontsize={},FontName={},PrimaryColour={},Outline={},MarginV=30'".format(
                    self.subtitle_path.replace(':', '\\:').replace('\'', '\\\''), 
                    self.font_size, self.font_name, self.font_color, self.outline_width
                ),
                1: "subtitles='{}':force_style='Fontsize={},FontName={},PrimaryColour={},Outline={},MarginV=30,Alignment=6'".format(
                    self.subtitle_path.replace(':', '\\:').replace('\'', '\\\''), 
                    self.font_size, self.font_name, self.font_color, self.outline_width
                ),
                2: "subtitles='{}':force_style='Fontsize={},FontName={},PrimaryColour={},Outline={},MarginV=30,Alignment=10'".format(
                    self.subtitle_path.replace(':', '\\:').replace('\'', '\\\''), 
                    self.font_size, self.font_name, self.font_color, self.outline_width
                )
            }
            
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', self.video_path, 
                '-vf', position_map[self.position],
                '-c:v', 'libx264', '-crf', '18', 
                '-c:a', 'copy', self.output_path
            ]
            
            # Create process and read output line by line to update progress
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True
            )
            
            # Progress tracking
            for line in process.stdout:
                if "time=" in line:
                    time_str = line.split("time=")[1].split()[0]
                    h, m, s = map(float, time_str.split(':'))
                    current_time = h * 3600 + m * 60 + s
                    progress = int((current_time / duration) * 100)
                    self.progress.emit(progress)
            
            # Wait for process to complete
            return_code = process.wait()
            if return_code == 0:
                self.finished.emit(True, "Subtitle burning completed successfully!")
            else:
                self.finished.emit(False, "Error during subtitle burning process.")
        
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class SubtitleBurnerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Subtitle Burner - Embed Subtitles into Videos')
        self.setMinimumSize(800, 600)
        
        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        
        # Video file selection
        self.video_path_label = QLabel("No video file selected")
        video_btn = QPushButton("Select Video", self)
        video_btn.clicked.connect(self.select_video)
        video_layout = QHBoxLayout()
        video_layout.addWidget(self.video_path_label, 1)
        video_layout.addWidget(video_btn)
        file_layout.addRow("Video File:", video_layout)
        
        # Subtitle file selection
        self.subtitle_path_label = QLabel("No subtitle file selected")
        subtitle_btn = QPushButton("Select Subtitle", self)
        subtitle_btn.clicked.connect(self.select_subtitle)
        subtitle_layout = QHBoxLayout()
        subtitle_layout.addWidget(self.subtitle_path_label, 1)
        subtitle_layout.addWidget(subtitle_btn)
        file_layout.addRow("Subtitle File:", subtitle_layout)
        
        # Output file selection
        self.output_path_label = QLabel("No output location selected")
        output_btn = QPushButton("Save Output As", self)
        output_btn.clicked.connect(self.select_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_path_label, 1)
        output_layout.addWidget(output_btn)
        file_layout.addRow("Output File:", output_layout)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Subtitle appearance options
        appearance_group = QGroupBox("Subtitle Appearance")
        appearance_layout = QFormLayout()
        
        # Font selection
        self.font_combo = QComboBox()
        # Add common fonts
        common_fonts = ["Arial", "Helvetica", "Times New Roman", "Courier New", 
                       "Verdana", "Tahoma", "Impact", "Comic Sans MS"]
        self.font_combo.addItems(common_fonts)
        appearance_layout.addRow("Font:", self.font_combo)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 72)
        self.font_size.setValue(24)
        appearance_layout.addRow("Size:", self.font_size)
        
        # Font color
        self.color_btn = QPushButton("Select Color")
        self.color_btn.clicked.connect(self.select_color)
        self.font_color = "&Hffffff" # White by default
        self.color_preview = QLabel("■")
        self.color_preview.setStyleSheet("color: white; font-size: 24px;")
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_btn)
        appearance_layout.addRow("Color:", color_layout)
        
        # Outline width
        self.outline_width = QSpinBox()
        self.outline_width.setRange(0, 4)
        self.outline_width.setValue(1)
        appearance_layout.addRow("Outline:", self.outline_width)
        
        # Position selection
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Bottom", "Top", "Middle"])
        appearance_layout.addRow("Position:", self.position_combo)
        
        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)
        
        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # Process button
        self.burn_btn = QPushButton("Burn Subtitles", self)
        self.burn_btn.clicked.connect(self.burn_subtitles)
        self.burn_btn.setMinimumHeight(50)
        self.burn_btn.setEnabled(False)
        main_layout.addWidget(self.burn_btn)
        
        self.setCentralWidget(main_widget)
        
    def select_video(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv);;All Files (*)", 
            options=options)
            
        if file_path:
            self.video_path_label.setText(file_path)
            self.check_burn_enabled()
            
            # Auto-suggest output filename
            if not self.output_path_label.text() or self.output_path_label.text() == "No output location selected":
                dir_name = os.path.dirname(file_path)
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                suggested_output = os.path.join(dir_name, f"{name}_subtitled{ext}")
                self.output_path_label.setText(suggested_output)
    
    def select_subtitle(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", "", 
            "Subtitle Files (*.srt *.ass *.ssa *.vtt);;All Files (*)", 
            options=options)
            
        if file_path:
            self.subtitle_path_label.setText(file_path)
            self.check_burn_enabled()
    
    def select_output(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Output Video As", "", 
            "Video Files (*.mp4 *.mkv);;All Files (*)", 
            options=options)
            
        if file_path:
            # Add extension if not provided
            if not os.path.splitext(file_path)[1]:
                file_path += ".mp4"
                
            self.output_path_label.setText(file_path)
            self.check_burn_enabled()
    
    def select_color(self):
        color = QColorDialog.getColor(Qt.white, self, "Select Font Color")
        if color.isValid():
            # Convert to ASS color format (BGR in hex)
            hex_color = f"&H{color.blue():02x}{color.green():02x}{color.red():02x}"
            self.font_color = hex_color
            self.color_preview.setStyleSheet(f"color: {color.name()}; font-size: 24px;")
    
    def check_burn_enabled(self):
        video_selected = self.video_path_label.text() != "No video file selected"
        subtitle_selected = self.subtitle_path_label.text() != "No subtitle file selected"
        output_selected = self.output_path_label.text() != "No output location selected"
        
        self.burn_btn.setEnabled(video_selected and subtitle_selected and output_selected)
    
    def burn_subtitles(self):
        video_path = self.video_path_label.text()
        subtitle_path = self.subtitle_path_label.text()
        output_path = self.output_path_label.text()
        
        # Check if files exist
        if not os.path.exists(video_path):
            QMessageBox.critical(self, "Error", "Video file does not exist!")
            return
            
        if not os.path.exists(subtitle_path):
            QMessageBox.critical(self, "Error", "Subtitle file does not exist!")
            return
        
        # Update UI
        self.burn_btn.setEnabled(False)
        self.status_label.setText("Processing...")
        self.progress_bar.setValue(0)
        
        # Get subtitle options
        font_size = self.font_size.value()
        font_name = self.font_combo.currentText()
        font_color = self.font_color
        position = self.position_combo.currentIndex()
        outline = self.outline_width.value()
        
        # Start processing thread
        self.thread = SubtitleBurnerThread(
            video_path, subtitle_path, output_path, 
            font_size, font_name, font_color, position, outline
        )
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.burning_finished)
        self.thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def burning_finished(self, success, message):
        self.burn_btn.setEnabled(True)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Check if ffmpeg and ffprobe are available
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        QMessageBox.critical(None, "Error", 
                           "FFmpeg not found! Please install FFmpeg and make sure it's in your system PATH.")
        sys.exit(1)
    
    window = SubtitleBurnerApp()
    window.show()
    sys.exit(app.exec_())
