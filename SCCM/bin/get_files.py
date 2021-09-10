from tkinter import Tk, filedialog


def choose_files_for_import():
    """
    Opens operating system file folder to choose one or more input files for processing
    :return: list of one or more files
    """
    # disable root modal window
    root = Tk()
    root.withdraw()
    # prompt for directory path, results stored as tuple
    tk_filenames = filedialog.askopenfilenames()
    root.update()
    root.destroy()
    return tk_filenames
