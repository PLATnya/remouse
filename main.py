import tkinter as tk
from gui import MouseControllerApp

def main():
    root = tk.Tk()
    app = MouseControllerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
