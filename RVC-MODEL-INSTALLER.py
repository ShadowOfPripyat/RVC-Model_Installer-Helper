import sys
import os
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QInputDialog, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, QMimeData, QTimer


INSTALLER_PATH_FILE = Path('RVC_MODEL_INSTALLER_FOLDER.txt')
DEFAULT_MODELS_PATH = Path(r"C:\AI Programs\Retrieval-based-Voice-Conversion-WebUI\models\rvc_models")

def get_model_path():
    if INSTALLER_PATH_FILE.exists():
        try:
            path = INSTALLER_PATH_FILE.read_text(encoding='utf-8').strip()
            if path:
                return Path(path)
        except Exception:
            pass
    return DEFAULT_MODELS_PATH

def set_model_path(path):
    INSTALLER_PATH_FILE.write_text(str(path), encoding='utf-8')


class DropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent_installer = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        local_paths = [url.toLocalFile() for url in urls]
        if self.parent_installer:
            # Pass all paths as a list if more than one file is dropped
            if len(local_paths) > 1:
                self.parent_installer.handle_dropped_item(local_paths)
            else:
                self.parent_installer.handle_dropped_item(local_paths[0])
        if self.parent_installer:
            self.parent_installer.load_models()
        event.acceptProposedAction()

class ModelInstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RVC Model Installer")
        self.resize(600, 400)

        # Model path selection
        self.model_path = get_model_path()
        self.path_edit = QLineEdit(str(self.model_path))
        self.path_edit.setStyleSheet("font-size: 15px; padding: 6px;")
        self.browse_button = QPushButton("Browse")
        self.browse_button.setStyleSheet("font-size: 15px; padding: 6px;")
        self.browse_button.clicked.connect(self.browse_model_path)
        self.path_edit.editingFinished.connect(self.update_model_path_from_text)
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Model Folder:"))
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)

        # Left: Model list
        self.model_list = QListWidget()
        self.model_list.setStyleSheet("font-size: 18px; padding: 8px;")
        self.load_models()

        # Buttons for remove, rename, and refresh
        self.remove_button = QPushButton("Remove Model")
        self.remove_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.remove_button.clicked.connect(self.remove_model)
        self.rename_button = QPushButton("Rename Model")
        self.rename_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.rename_button.clicked.connect(self.rename_model)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.refresh_button.clicked.connect(self.load_models)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.rename_button)
        button_layout.addWidget(self.refresh_button)

        left_layout = QVBoxLayout()
        left_layout.addLayout(path_layout)
        left_layout.addWidget(self.model_list)
        left_layout.addLayout(button_layout)

        # Right: Drop area
        self.drop_label = DropLabel(self)
        self.drop_label.setText("Drag and drop model files/folders here")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; font-size: 20px; padding: 30px; }")

        # Layout
        h_layout = QHBoxLayout()
        h_layout.addLayout(left_layout, 1)
        h_layout.addWidget(self.drop_label, 3)
        self.setLayout(h_layout)

        # Timer to refresh model list every 30 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_models)
        self.timer.start(30000)  # 30 seconds
    
    def browse_model_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Model Folder", str(self.model_path))
        if folder:
            self.path_edit.setText(folder)
            self.update_model_path_from_text()

    def update_model_path_from_text(self):
        new_path = Path(self.path_edit.text().strip())
        if new_path != self.model_path:
            self.model_path = new_path
            set_model_path(self.model_path)
            self.load_models()

    def load_models(self):
        self.model_list.clear()
        if not self.model_path.exists():
            self.model_path.mkdir(parents=True)
        for folder in sorted(self.model_path.iterdir()):
            if folder.is_dir():
                # Check for .pth and .index files
                has_pth = any(f.suffix == ".pth" for f in folder.iterdir() if f.is_file())
                has_index = any(f.suffix == ".index" for f in folder.iterdir() if f.is_file())
                has_any = any(True for _ in folder.iterdir())
                display_name = folder.name
                tooltip = None
                if not has_any:
                    display_name += " ❔"
                    tooltip = "Folder is empty."
                elif not has_pth or not has_index:
                    display_name += " ⚠️"
                    missing = []
                    if not has_pth:
                        missing.append(".pth")
                    if not has_index:
                        missing.append(".index")
                    tooltip = f"Missing {', '.join(missing)} file(s). Model won't work."
                item = self.model_list.addItem(display_name)
                if tooltip:
                    self.model_list.item(self.model_list.count()-1).setToolTip(tooltip)

    def handle_dropped_item(self, path):
        # If multiple files are dropped, handle them together
        if isinstance(path, list):
            files = [Path(p) for p in path]
            pth_files = [f for f in files if f.suffix == ".pth"]
            index_files = [f for f in files if f.suffix == ".index"]
            if len(pth_files) == 1 and len(index_files) == 1:
                pth_file = pth_files[0]
                index_file = index_files[0]
                model_name = pth_file.stem
                dest_folder = self.model_path / model_name
                counter = 1
                while dest_folder.exists():
                    dest_folder = self.model_path / f"{model_name}_{counter}"
                    counter += 1
                try:
                    dest_folder.mkdir(parents=True)
                    shutil.copy2(pth_file, dest_folder / pth_file.name)
                    shutil.copy2(index_file, dest_folder / index_file.name)
                except Exception as e:
                    QMessageBox.critical(self, "Copy Error", f"Failed to copy model files:\n{e}")
                return
            # If not both .pth and .index, just copy all files as separate models
            for f in files:
                self.handle_dropped_item(str(f))
            return

        source = Path(path)
        if not source.exists():
            QMessageBox.warning(self, "Error", f"Path does not exist:\n{path}")
            return

        # If it's a .pth file, create a folder with the same name (without extension) and move the file inside
        if source.is_file() and source.suffix == ".pth":
            model_name = source.stem
            dest_folder = self.model_path / model_name
            counter = 1
            while dest_folder.exists():
                dest_folder = self.model_path / f"{model_name}_{counter}"
                counter += 1
            try:
                dest_folder.mkdir(parents=True)
                shutil.copy2(source, dest_folder / source.name)
            except Exception as e:
                QMessageBox.critical(self, "Copy Error", f"Failed to copy .pth file:\n{e}")
            return

        # Use the file/folder name as model name for other files/folders
        model_name = source.stem if source.is_file() else source.name
        dest = self.model_path / model_name
        counter = 1
        while dest.exists():
            dest = self.model_path / f"{model_name}_{counter}"
            counter += 1
        try:
            if source.is_file():
                shutil.copy2(source, dest)
            else:
                shutil.copytree(source, dest)
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Failed to copy:\n{e}")

    def remove_model(self):
        selected = self.model_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "No Selection", "Please select a model to remove.")
            return
        # Get the real folder name from the filesystem
        folders = [f for f in sorted(self.model_path.iterdir()) if f.is_dir()]
        if selected >= len(folders):
            QMessageBox.warning(self, "Error", "Selected model does not exist.")
            return
        model_path = folders[selected]
        model_name = model_path.name
        reply = QMessageBox.question(self, "Remove Model", f"Are you sure you want to remove '{model_name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(model_path)
                self.load_models()
            except Exception as e:
                QMessageBox.critical(self, "Remove Error", f"Failed to remove model:\n{e}")

    def rename_model(self):
        selected = self.model_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a model to rename.")
            return
        model_name = selected.text()
        model_path = self.model_path / model_name
        new_name, ok = QInputDialog.getText(self, "Rename Model", "Enter new model name:", text=model_name)
        if ok and new_name and new_name != model_name:
            new_path = self.model_path / new_name
            if new_path.exists():
                QMessageBox.warning(self, "Rename Error", "A model with that name already exists.")
                return
            try:
                model_path.rename(new_path)
                self.load_models()
            except Exception as e:
                QMessageBox.critical(self, "Rename Error", f"Failed to rename model:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModelInstaller()
    window.show()
    sys.exit(app.exec())
