import sys
import requests
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QLabel, QLineEdit, QPushButton)
from PyQt6.QtCore import QThread, pyqtSignal, Qt


class NetworkWorker(QThread):
    success_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, key):
        super().__init__()
        self.key = key

    def run(self):
        try:
            url = "http://localhost:8000/api/activate-key"
            response = requests.post(url, json={"activation_key": self.key}, timeout=5)
            data = response.json()

            if response.status_code == 200:
                self.success_signal.emit(data)
            else:
                self.error_signal.emit(data.get('detail', 'Неверный ключ'))

        except requests.exceptions.ConnectionError:
            self.error_signal.emit("Ошибка: Сервер недоступен (Докер запущен?)")
        except Exception as e:
            self.error_signal.emit(f"Неизвестная ошибка: {str(e)}")


class ClientWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_session_key = None
        self.setWindowTitle("Proxy Access Client")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Подключение к Proxy")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Введите ваш 32-значный ключ...")
        self.key_input.setStyleSheet("padding: 8px; font-family: Consolas; font-size: 14px;")
        layout.addWidget(self.key_input)

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.setStyleSheet(
            "padding: 10px; font-size: 14px; font-weight: bold; background-color: #1976D2; color: white; border-radius: 4px;")
        self.connect_btn.clicked.connect(self.start_connection)
        layout.addWidget(self.connect_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("margin-top: 15px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def start_connection(self):
        key = self.key_input.text().strip()
        if len(key) != 32:
            self.show_status("Ошибка: Ключ должен быть 32 символа", "red")
            return

        self.show_status("Подключение к серверу...", "orange")
        self.connect_btn.setEnabled(False)

        self.worker = NetworkWorker(key)
        self.worker.success_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def on_success(self, data):
        self.connect_btn.setEnabled(True)
        self.current_session_key = data.get("new_key")

        vm_name = data.get("vm_name", "Неизвестно")
        ip = data.get("vm_ip", "0.0.0.0")
        self.show_status(f"Успешно выдана ВМ: {vm_name}\nIP: {ip}", "green")

    def on_error(self, error_msg):
        self.connect_btn.setEnabled(True)
        self.show_status(f"Отказ: {error_msg}", "red")

    def show_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"margin-top: 15px; font-weight: bold; color: {color};")

    def closeEvent(self, event):
        if hasattr(self, 'current_session_key') and self.current_session_key:
            try:
                requests.post(
                    "http://localhost:8000/api/disconnect",
                    json={"activation_key": self.current_session_key},
                    timeout=2
                )
            except Exception:
                pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    window = ClientWindow()
    window.show()
    sys.exit(app.exec())