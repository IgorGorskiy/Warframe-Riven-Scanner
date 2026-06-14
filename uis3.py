# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitled.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGraphicsView, QGridLayout,
    QHBoxLayout, QLCDNumber, QLabel, QLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenuBar, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSizePolicy, QSlider, QSpacerItem,
    QStatusBar, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1600, 800)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QSize(1600, 700))
        MainWindow.setSizeIncrement(QSize(1, 1))
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setSizeIncrement(QSize(1, 1))
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setObjectName(u"mainLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy1)
        self.tabWidget.setSizeIncrement(QSize(1, 1))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        sizePolicy.setHeightForWidth(self.tab.sizePolicy().hasHeightForWidth())
        self.tab.setSizePolicy(sizePolicy)
        self.tab.setSizeIncrement(QSize(1, 1))
        self.horizontalLayout = QHBoxLayout(self.tab)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.rivensLayout = QHBoxLayout()
        self.rivensLayout.setObjectName(u"rivensLayout")
        self.rivensLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.radioButton = QRadioButton(self.tab)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setChecked(True)

        self.verticalLayout_6.addWidget(self.radioButton)

        self.listWidget = QListWidget(self.tab)
        self.listWidget.setObjectName(u"listWidget")
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy)
        self.listWidget.setMinimumSize(QSize(750, 200))
        self.listWidget.setMaximumSize(QSize(750, 16777215))
        self.listWidget.setSizeIncrement(QSize(1, 1))

        self.verticalLayout_6.addWidget(self.listWidget)


        self.rivensLayout.addLayout(self.verticalLayout_6)

        self.scrollArea = QScrollArea(self.tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setMinimumSize(QSize(450, 0))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 758, 816))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.rivenDataLayout = QVBoxLayout()
        self.rivenDataLayout.setObjectName(u"rivenDataLayout")
        self.pushButton = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton.setObjectName(u"pushButton")

        self.rivenDataLayout.addWidget(self.pushButton)

        self.scansAmountLayout = QHBoxLayout()
        self.scansAmountLayout.setObjectName(u"scansAmountLayout")
        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")

        self.scansAmountLayout.addWidget(self.label)

        self.seconds_from_update = QLCDNumber(self.scrollAreaWidgetContents)
        self.seconds_from_update.setObjectName(u"seconds_from_update")
        self.seconds_from_update.setMaximumSize(QSize(64, 40))

        self.scansAmountLayout.addWidget(self.seconds_from_update)

        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(0, 40))
        self.label_2.setMaximumSize(QSize(16777215, 40))

        self.scansAmountLayout.addWidget(self.label_2)

        self.updatesLCD = QLCDNumber(self.scrollAreaWidgetContents)
        self.updatesLCD.setObjectName(u"updatesLCD")
        self.updatesLCD.setMinimumSize(QSize(64, 40))
        self.updatesLCD.setMaximumSize(QSize(64, 40))

        self.scansAmountLayout.addWidget(self.updatesLCD)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.scansAmountLayout.addItem(self.horizontalSpacer)


        self.rivenDataLayout.addLayout(self.scansAmountLayout)

        self.progressLayout = QVBoxLayout()
        self.progressLayout.setObjectName(u"progressLayout")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_6.addWidget(self.label_3)

        self.podRollProgress = QProgressBar(self.scrollAreaWidgetContents)
        self.podRollProgress.setObjectName(u"podRollProgress")
        self.podRollProgress.setMinimumSize(QSize(100, 0))
        self.podRollProgress.setMaximumSize(QSize(1000, 16777215))
        self.podRollProgress.setMaximum(100)
        self.podRollProgress.setValue(0)

        self.horizontalLayout_6.addWidget(self.podRollProgress)

        self.podRollProgressLCD = QLCDNumber(self.scrollAreaWidgetContents)
        self.podRollProgressLCD.setObjectName(u"podRollProgressLCD")
        self.podRollProgressLCD.setMinimumSize(QSize(0, 30))
        self.podRollProgressLCD.setMaximumSize(QSize(60, 16777215))

        self.horizontalLayout_6.addWidget(self.podRollProgressLCD)


        self.progressLayout.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_7.addWidget(self.label_5)

        self.grollProgress = QProgressBar(self.scrollAreaWidgetContents)
        self.grollProgress.setObjectName(u"grollProgress")
        self.grollProgress.setMinimumSize(QSize(100, 0))
        self.grollProgress.setMaximumSize(QSize(1000, 16777215))
        self.grollProgress.setValue(0)

        self.horizontalLayout_7.addWidget(self.grollProgress)

        self.grollProgressLCD = QLCDNumber(self.scrollAreaWidgetContents)
        self.grollProgressLCD.setObjectName(u"grollProgressLCD")
        self.grollProgressLCD.setMinimumSize(QSize(0, 30))
        self.grollProgressLCD.setMaximumSize(QSize(60, 16777215))
        self.grollProgressLCD.setProperty(u"intValue", 0)

        self.horizontalLayout_7.addWidget(self.grollProgressLCD)


        self.progressLayout.addLayout(self.horizontalLayout_7)


        self.rivenDataLayout.addLayout(self.progressLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.weaponComboBox = QComboBox(self.scrollAreaWidgetContents)
        self.weaponComboBox.setObjectName(u"weaponComboBox")

        self.horizontalLayout_2.addWidget(self.weaponComboBox)

        self.buildWeaponPlot = QPushButton(self.scrollAreaWidgetContents)
        self.buildWeaponPlot.setObjectName(u"buildWeaponPlot")

        self.horizontalLayout_2.addWidget(self.buildWeaponPlot)


        self.rivenDataLayout.addLayout(self.horizontalLayout_2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.plotsCount = QLineEdit(self.scrollAreaWidgetContents)
        self.plotsCount.setObjectName(u"plotsCount")

        self.gridLayout.addWidget(self.plotsCount, 0, 1, 1, 1)

        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)


        self.rivenDataLayout.addLayout(self.gridLayout)

        self.weaponPlot = QGraphicsView(self.scrollAreaWidgetContents)
        self.weaponPlot.setObjectName(u"weaponPlot")
        self.weaponPlot.setMinimumSize(QSize(300, 250))

        self.rivenDataLayout.addWidget(self.weaponPlot)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.grollWeaponComboBoX = QComboBox(self.scrollAreaWidgetContents)
        self.grollWeaponComboBoX.setObjectName(u"grollWeaponComboBoX")

        self.horizontalLayout_3.addWidget(self.grollWeaponComboBoX)

        self.showGrollRivensForStats = QPushButton(self.scrollAreaWidgetContents)
        self.showGrollRivensForStats.setObjectName(u"showGrollRivensForStats")

        self.horizontalLayout_3.addWidget(self.showGrollRivensForStats)

        self.buildGrollPlot = QPushButton(self.scrollAreaWidgetContents)
        self.buildGrollPlot.setObjectName(u"buildGrollPlot")

        self.horizontalLayout_3.addWidget(self.buildGrollPlot)


        self.rivenDataLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.stat1 = QComboBox(self.scrollAreaWidgetContents)
        self.stat1.setObjectName(u"stat1")

        self.horizontalLayout_5.addWidget(self.stat1)

        self.stat2 = QComboBox(self.scrollAreaWidgetContents)
        self.stat2.setObjectName(u"stat2")

        self.horizontalLayout_5.addWidget(self.stat2)

        self.stat3 = QComboBox(self.scrollAreaWidgetContents)
        self.stat3.setObjectName(u"stat3")

        self.horizontalLayout_5.addWidget(self.stat3)

        self.stat4 = QComboBox(self.scrollAreaWidgetContents)
        self.stat4.setObjectName(u"stat4")

        self.horizontalLayout_5.addWidget(self.stat4)


        self.rivenDataLayout.addLayout(self.horizontalLayout_5)

        self.grollPlot = QGraphicsView(self.scrollAreaWidgetContents)
        self.grollPlot.setObjectName(u"grollPlot")
        self.grollPlot.setMinimumSize(QSize(300, 250))

        self.rivenDataLayout.addWidget(self.grollPlot)


        self.verticalLayout_2.addLayout(self.rivenDataLayout)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.rivensLayout.addWidget(self.scrollArea)


        self.horizontalLayout.addLayout(self.rivensLayout)

        self.tabWidget.addTab(self.tab, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.horizontalLayout_4 = QHBoxLayout(self.tab_4)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.pigLayout = QVBoxLayout()
        self.pigLayout.setObjectName(u"pigLayout")

        self.horizontalLayout_4.addLayout(self.pigLayout)

        self.tabWidget.addTab(self.tab_4, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        sizePolicy.setHeightForWidth(self.tab_2.sizePolicy().hasHeightForWidth())
        self.tab_2.setSizePolicy(sizePolicy)
        self.tab_2.setSizeIncrement(QSize(1, 1))
        self.horizontalLayout_41 = QHBoxLayout(self.tab_2)
        self.horizontalLayout_41.setObjectName(u"horizontalLayout_41")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_8 = QLabel(self.tab_2)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_4.addWidget(self.label_8)

        self.label_9 = QLabel(self.tab_2)
        self.label_9.setObjectName(u"label_9")

        self.verticalLayout_4.addWidget(self.label_9)

        self.label_10 = QLabel(self.tab_2)
        self.label_10.setObjectName(u"label_10")

        self.verticalLayout_4.addWidget(self.label_10)

        self.label_11 = QLabel(self.tab_2)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_4.addWidget(self.label_11)

        self.stage_label = QLabel(self.tab_2)
        self.stage_label.setObjectName(u"stage_label")

        self.verticalLayout_4.addWidget(self.stage_label)

        self.scheduleText = QTextEdit(self.tab_2)
        self.scheduleText.setObjectName(u"scheduleText")

        self.verticalLayout_4.addWidget(self.scheduleText)

        self.saveScheduleBtn = QPushButton(self.tab_2)
        self.saveScheduleBtn.setObjectName(u"saveScheduleBtn")

        self.verticalLayout_4.addWidget(self.saveScheduleBtn)

        self.label_12 = QLabel(self.tab_2)
        self.label_12.setObjectName(u"label_12")

        self.verticalLayout_4.addWidget(self.label_12)

        self.cooldownComboBox = QComboBox(self.tab_2)
        self.cooldownComboBox.setObjectName(u"cooldownComboBox")

        self.verticalLayout_4.addWidget(self.cooldownComboBox)

        self.cooldownInput = QLineEdit(self.tab_2)
        self.cooldownInput.setObjectName(u"cooldownInput")

        self.verticalLayout_4.addWidget(self.cooldownInput)

        self.saveCooldown = QPushButton(self.tab_2)
        self.saveCooldown.setObjectName(u"saveCooldown")

        self.verticalLayout_4.addWidget(self.saveCooldown)


        self.horizontalLayout_8.addLayout(self.verticalLayout_4)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_6 = QLabel(self.tab_2)
        self.label_6.setObjectName(u"label_6")

        self.verticalLayout_3.addWidget(self.label_6)

        self.podRollText = QTextEdit(self.tab_2)
        self.podRollText.setObjectName(u"podRollText")

        self.verticalLayout_3.addWidget(self.podRollText)

        self.savePodRollBtn = QPushButton(self.tab_2)
        self.savePodRollBtn.setObjectName(u"savePodRollBtn")

        self.verticalLayout_3.addWidget(self.savePodRollBtn)

        self.label_7 = QLabel(self.tab_2)
        self.label_7.setObjectName(u"label_7")

        self.verticalLayout_3.addWidget(self.label_7)

        self.DBweaponsText = QTextEdit(self.tab_2)
        self.DBweaponsText.setObjectName(u"DBweaponsText")
        self.DBweaponsText.setMaximumSize(QSize(16777215, 150))

        self.verticalLayout_3.addWidget(self.DBweaponsText)

        self.saveBDweaponsBtn = QPushButton(self.tab_2)
        self.saveBDweaponsBtn.setObjectName(u"saveBDweaponsBtn")

        self.verticalLayout_3.addWidget(self.saveBDweaponsBtn)


        self.horizontalLayout_8.addLayout(self.verticalLayout_3)


        self.verticalLayout_5.addLayout(self.horizontalLayout_8)

        self.lineEdit = QLineEdit(self.tab_2)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setReadOnly(True)

        self.verticalLayout_5.addWidget(self.lineEdit)


        self.horizontalLayout_41.addLayout(self.verticalLayout_5)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        sizePolicy.setHeightForWidth(self.tab_3.sizePolicy().hasHeightForWidth())
        self.tab_3.setSizePolicy(sizePolicy)
        self.tab_3.setSizeIncrement(QSize(1, 1))
        self.horizontalLayout_42 = QHBoxLayout(self.tab_3)
        self.horizontalLayout_42.setObjectName(u"horizontalLayout_42")
        self.logsText = QTextEdit(self.tab_3)
        self.logsText.setObjectName(u"logsText")
        self.logsText.setReadOnly(True)

        self.horizontalLayout_42.addWidget(self.logsText)

        self.tabWidget.addTab(self.tab_3, "")
        self.tab_5 = QWidget()
        self.tab_5.setObjectName(u"tab_5")
        self.horizontalLayout_9 = QHBoxLayout(self.tab_5)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_13 = QLabel(self.tab_5)
        self.label_13.setObjectName(u"label_13")

        self.horizontalLayout_10.addWidget(self.label_13)

        self.volumeSlider = QSlider(self.tab_5)
        self.volumeSlider.setObjectName(u"volumeSlider")
        self.volumeSlider.setMaximumSize(QSize(300, 16777215))
        self.volumeSlider.setMaximum(99)
        self.volumeSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_10.addWidget(self.volumeSlider)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_2)


        self.verticalLayout_7.addLayout(self.horizontalLayout_10)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer)


        self.horizontalLayout_9.addLayout(self.verticalLayout_7)

        self.tabWidget.addTab(self.tab_5, "")

        self.mainLayout.addWidget(self.tabWidget)


        self.verticalLayout.addLayout(self.mainLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1600, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(4)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.radioButton.setText(QCoreApplication.translate("MainWindow", u"\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c/\u0432\u044b\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0443", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0432\u0435\u0441\u0442\u0438 \u043b\u043e\u0433\u0438", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0435\u043a\u0443\u043d\u0434 \u0441 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f:", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0439:", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0437\u0430\u043d\u043e\u0441\u0430 \u0446\u0435\u043d \u043f\u043e\u0434 \u0440\u043e\u043b\u043b \u0432 \u0431\u0434", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0441\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f groll \u0440\u0438\u0432\u0435\u043d\u043e\u0432", None))
        self.buildWeaponPlot.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0433\u0440\u0430\u0444\u0438\u043a \u0446\u0435\u043d\u044b \u043d\u0430 \u043e\u0440\u0443\u0436\u0438\u0435", None))
        self.plotsCount.setText(QCoreApplication.translate("MainWindow", u"1", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0437\u0438\u0446\u0438\u044f \u041c\u0420\u0430 (1 - \u043f\u0435\u0440\u0432\u044b\u0439 \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 \u043c\u0430\u0440\u043a\u0435\u0442\u0430)", None))
        self.showGrollRivensForStats.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0440\u0438\u0432\u0435\u043d\u044b", None))
        self.buildGrollPlot.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0433\u0440\u0430\u0444\u0438\u043a groll", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"\u0413\u043b\u0430\u0432\u043d\u0430\u044f", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("MainWindow", u"\u0421\u0432\u0438\u043d\u043a\u0430", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"\u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0438\u0442\u0435\u0440\u0430\u0446\u0438\u0438 \u0446\u0438\u043a\u043b\u0430 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b. \u041d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u043f\u0440\u0435\u0432\u044b\u0448\u0430\u0442\u044c 110 \u0441\u0435\u043a\u0443\u043d\u0434", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"WEAPON_FOR_DB_SEARCH - \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0440\u043e\u0435\u043d\u0438\u044f \u0433\u0440\u0430\u0444\u0438\u043a\u0430 \u0446\u0435\u043d\u044b \u043f\u043e\u0434 \u0440\u043e\u043b\u043b", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"GROLL - \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430 \u0445\u043e\u0440\u043e\u0448\u0438\u0445 \u0440\u0438\u0432\u0435\u043d\u043e\u0432 \u0432 \u043d\u0430\u0447\u0430\u043b\u0435 \u0440\u0430\u0431\u043e\u0442\u044b \u0438 \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0440\u043e\u0435\u043d\u0438\u044f \u0433\u0440\u0430\u0444\u0438\u043a\u0430 \u0446\u0435\u043d\u044b \u0445\u043e\u0440\u043e\u0448\u0438\u0445 \u0440\u0438\u0432\u0435\u043d\u043e\u0432", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"FAST_SEARCH - \u0431\u043e\u043b\u0435\u0435 \u043e\u043f\u0435\u0440\u0430\u0442\u0438\u0432\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0440\u0438\u0432\u0435\u043d\u043e\u0432 \u043f\u043e\u0434 \u0440\u043e\u043b\u043b \u043d\u0430 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u043e\u0435 \u043e\u0440\u0443\u0436\u0438\u0435", None))
        self.stage_label.setText(QCoreApplication.translate("MainWindow", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0440\u0435\u0436\u0438\u043c:", None))
        self.saveScheduleBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"\u0412\u0440\u0435\u043c\u044f \u043e\u0436\u0438\u0434\u0430\u043d\u0438\u044f \u043f\u043e\u0441\u043b\u0435 \u0437\u0430\u043f\u0440\u043e\u0441\u0430 (\u0432 \u0441\u0435\u043a\u0443\u043d\u0434\u0430\u0445)", None))
        self.saveCooldown.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0432\u0440\u0435\u043c\u044f \u043e\u0436\u0438\u0434\u0430\u043d\u0438\u044f", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0449\u0438\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u043e\u0440\u0443\u0436\u0438\u0439 \u0438 \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0445 \u0446\u0435\u043d", None))
        self.savePodRollBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043e\u0431\u0449\u0438\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u043e\u0440\u0443\u0436\u0438\u0439 \u0438 \u0446\u0435\u043d", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043f\u0438\u0441\u043e\u043a \u043e\u0440\u0443\u0436\u0438\u0439, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u0434\u043e\u043b\u0436\u043d\u044b \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0442\u044c\u0441\u044f \u0447\u0430\u0449\u0435 (FAST_SEARCH):", None))
        self.saveBDweaponsBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u043e\u0440\u0443\u0436\u0438\u0439, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u0434\u043e\u043b\u0436\u043d\u044b \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0442\u044c\u0441\u044f \u0447\u0430\u0441\u0442\u043e", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"\u041d\u043e\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0441\u043a\u0430\u043d\u0430", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"\u041b\u043e\u0433\u0438", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"\u0413\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c \u0434\u043e\u043b\u0431\u0451\u0436\u043a\u0438 \u0424\u0440\u0438\u0440\u0435\u043d", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_5), QCoreApplication.translate("MainWindow", u"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b", None))
    # retranslateUi

