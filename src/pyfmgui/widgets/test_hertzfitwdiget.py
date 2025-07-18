import sys
from pyqtgraph.Qt import QtWidgets
from pyfmgui.session import Session
from hertzfit_widget import HertzFitWidget

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    session = Session()
    widget = HertzFitWidget(session)
    widget.show()
    sys.exit(app.exec_())