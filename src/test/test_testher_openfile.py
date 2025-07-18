import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from pyqtgraph.Qt import QtWidgets
# from pyfmgui.session import Session

from pyfmgui.main_window import MainWindow
from pyfmgui.session import Session

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    session = Session()
    window = MainWindow(session)
    window.show()



    # Specify your folder or file path here
    # folder_path = '/Users/evillz/Data/article/2025_07_01_THP1_phd/cell2'
    # folder_path = '/Users/evillz/Data/article/2025_07_01_THP1_phd/cell2/1000_4'
    folder_path = '/Users/evillz/Data/article/2025_07_01_THP1_phd/cell2/300'

    # Get all valid files in the folder
    file_list = window.getFileList(folder_path)
    print("Found files:")
    for f in file_list[:5:] + file_list[-5:]:  # Print only the first 5 files for brevity and last 5
        print(f)

    # Load the files using the MainWindow method
    if file_list:
        window.load_files(file_list)

    # Wait for the files to finish loading before proceeding
    app.processEvents()  # Process any pending events (including file loading if async)

    # # Open the TetherViewerWidget as if triggered from the GUI
    # action = QtWidgets.QAction("Tether Viewer (Debug)", window)
    # action.triggered.connect(window.open_analysis_window)
    # action.trigger()

    # Open the Data Viewer as if triggered from the GUI
    # openDataViewer = QtWidgets.QAction("Data Viewer", window)
    # openDataViewer.setToolTip("Open Data Viewer window.")
    # openDataViewer.triggered.connect(window.open_analysis_window)
    # openDataViewer.trigger()


    sys.exit(app.exec_())