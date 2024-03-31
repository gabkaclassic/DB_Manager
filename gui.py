import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from environs import Env
from sqlalchemy import create_engine, MetaData, Table, desc
from sqlalchemy.engine import reflection


env = Env()
env.read_env()

db_password = env.str("DB_PASSWORD")
db_username = env.str("DB_USERNAME")
db_name = env.str("DB_NAME")
db_host = env.str("DB_HOST")
default_table = env.str("DEFAULT_TABLE")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connect()
        self.set_table()
        self.initialize()

    def initialize(self, current_table_name=None):

        self.setWindowTitle("Table manager")
        self.setGeometry(100, 100, 800, 600)

        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(len(self.db_table.columns))
        self.table.setHorizontalHeaderLabels(
            [column.name for column in self.db_table.columns]
        )

        self.layout = QVBoxLayout()

        self.search_initialize()
        self.update_initialize()
        self.insert_initialize()
        self.delete_initialize()

        self.table_name = QComboBox()
        inspector = reflection.Inspector.from_engine(self.engine)
        self.table_name.addItems([table for table in inspector.get_table_names()])
        if current_table_name:
            self.table_name.setCurrentText(current_table_name)
        self.table_name.currentIndexChanged.connect(self.set_table)

        self.layout.addWidget(self.table_name)

        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        self.search()

    def update_initialize(self):
        self.update_column = QComboBox()
        self.update_column.addItems([column.name for column in self.db_table.columns])
        self.update_value_textbox = QtWidgets.QLineEdit()
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_record)
        self.layout.addWidget(self.update_button)

    def search_initialize(self):
        self.search_field_dropdown = QComboBox()
        self.search_field_dropdown.addItems(
            ["", *[column.name for column in self.db_table.columns]]
        )

        self.search_value_textbox = QtWidgets.QLineEdit()

        self.search_button = QPushButton("Select")
        self.search_button.clicked.connect(self.search)

        self.sorting_dropdown = QComboBox()
        self.sorting_dropdown.addItems(
            [column.name for column in self.db_table.columns]
        )
        self.sorting_order = QComboBox()
        self.sorting_order.addItems(["ASC", "DESC"])
        self.sorting_order.currentIndexChanged.connect(self.search)

        self.limit_dropdown = QComboBox()
        self.limit_dropdown.addItems(["10", "25", "50", "100"])
        self.limit_dropdown.currentIndexChanged.connect(self.search)

        self.limit_label = QLabel("Limit:")

        self.layout.addWidget(self.table)
        self.layout.addWidget(self.search_field_dropdown)
        self.layout.addWidget(self.search_value_textbox)
        self.layout.addWidget(self.search_button)
        self.layout.addWidget(self.sorting_dropdown)
        self.layout.addWidget(self.sorting_order)
        self.layout.addWidget(self.limit_label)
        self.layout.addWidget(self.limit_dropdown)

    def insert_initialize(self):

        self.add_button = QPushButton("Add Record")
        self.add_button.clicked.connect(self.add_record)
        self.layout.addWidget(self.add_button)

    def delete_initialize(self):
        self.delete_button = QPushButton("Delete Record")
        self.delete_button.clicked.connect(self.delete_record)
        self.layout.addWidget(self.delete_button)

    def set_table(self):
        try:
            table_name = self.table_name.currentText()
        except:
            table_name = default_table

        self.db_table = Table(table_name, self.metadata, autoload_with=self.engine)
        self.initialize(table_name)

    def connect(self):
        self.metadata = MetaData()
        self.engine = create_engine(
            f"mssql+pymssql://{db_username}:{db_password}@{db_host}/{db_name}"
        )
        self.metadata.reflect(bind=self.engine)
        self.connection = self.engine.connect()

    def search(self):
        search_field = self.search_field_dropdown.currentText()
        search_value = self.search_value_textbox.text()

        stmt = self.db_table.select()
        if search_field and search_value:
            stmt = stmt.where(getattr(self.db_table.c, search_field) == search_value)

        limit = int(self.limit_dropdown.currentText())

        if limit:
            stmt = stmt.limit(limit)

        sorting_field = self.sorting_dropdown.currentText()
        if sorting_field:
            desc_order = self.sorting_order.currentText() == "DESC"
            field = (
                desc(getattr(self.db_table.c, sorting_field))
                if desc_order
                else getattr(self.db_table.c, sorting_field)
            )
            stmt = stmt.order_by(field)

        result = self.connection.execute(stmt)
        records = result.fetchall()

        self.table.setRowCount(0)

        for i, record in enumerate(records):
            self.table.insertRow(i)
            for j, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                self.table.setItem(i, j, item)

    def update_record(self):

        row = self.table.currentRow()
        column = self.table.currentColumn()

        current_value = self.table.item(row, column).text()
        new_value, ok = QtWidgets.QInputDialog.getText(
            self,
            "Update Record",
            f"Enter a new value for {self.db_table.columns[column].name}:",
            text=current_value,
        )

        if ok:
            record = self.table.item(row, 0).text()
            self.table.setItem(row, column, QTableWidgetItem(new_value))

            column_name = self.db_table.columns.keys()[column]

            update_statement = (
                self.db_table.update()
                .where(self.db_table.columns[0] == record[0])
                .values({column_name: new_value})
            )
            self.connection.execute(update_statement)

    def add_record(self):
        add_dialog = QtWidgets.QDialog()
        add_dialog.setWindowTitle("Add Record")

        layout = QVBoxLayout()

        fields = {}
        for column in self.db_table.columns:
            label = QLabel(column.name)
            line_edit = QtWidgets.QLineEdit()
            fields[column.name] = line_edit
            layout.addWidget(label)
            layout.addWidget(line_edit)

        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_new_record(fields, add_dialog))
        layout.addWidget(add_button)

        add_dialog.setLayout(layout)
        add_dialog.exec_()

    def add_new_record(self, fields, dialog):
        new_values = {}
        for column_name, line_edit in fields.items():
            new_values[column_name] = line_edit.text()

        ins = self.db_table.insert().values(new_values)
        self.connection.execute(ins)

        dialog.close()
        self.search()

    def delete_record(self):
        selected_row = self.table.currentRow()
        if selected_row != -1:
            record_id = self.table.item(selected_row, 0).text()
            delete_confirmation = QtWidgets.QMessageBox.question(
                self,
                "Delete Record",
                "Are you sure you want to delete this record?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if delete_confirmation == QtWidgets.QMessageBox.Yes:
                del_stmt = self.db_table.delete().where(
                    self.db_table.columns[0] == record_id
                )
                self.connection.execute(del_stmt)
                self.search()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
