import sys
from PyQt6.QtWidgets import QApplication
from gui import MouseControllerApp


def main():
    app = QApplication(sys.argv)
    window = MouseControllerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
