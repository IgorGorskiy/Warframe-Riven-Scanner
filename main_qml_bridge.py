"""
main_qml_bridge.py
~~~~~~~~~~~~~~~~~~
Мост между Python-логикой и QML главным окном.
Заменяет uis3.py (Ui_MainWindow).

Подключение:
    from main_qml_bridge import MainWindowBridge

    bridge = MainWindowBridge()
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("mainBridge", bridge)
    ctx.setContextProperty("rivenModel", riven_model)
    engine.load(QUrl.fromLocalFile("MainWindow.qml"))

Таблица совместимости (оригинальный виджет → новый API):
    ui.seconds_from_update.display(n)    →  bridge.setSecondsFromUpdate(n)
    ui.updatesLCD.display(n)             →  bridge.setUpdatesCount(n)
    ui.podRollProgress.setValue(v)       →  bridge.setPodRollProgress(v, max)
    ui.grollProgress.setValue(v)         →  bridge.setGrollProgress(v, max)
    ui.radioButton.isChecked()           →  bridge.programEnabled  (свойство)
    ui.stage_label.setText(t)            →  bridge.setCurrentStage(t)
    ui.logsText.append(t)               →  bridge.appendLog(t)
    ui.lineEdit.setText(t)              →  bridge.setStatusLine(t)
    ui.weaponComboBox / grollWeaponComboBoX  →  bridge.setWeaponList([...])
    ui.stat1..4.addItems([...])         →  bridge.setStatNames([...])
    ui.scheduleText.(get/set)           →  bridge.scheduleText / setScheduleText()
    ui.podRollText.(get/set)            →  bridge.podRollText / setPodRollText()
    ui.DBweaponsText.(get/set)          →  bridge.dbWeaponsText / setDbWeaponsText()
    ui.cooldownComboBox / cooldownInput →  bridge.setWeaponList / setCooldownValue()
    ui.weaponPlot  (QGraphicsView)      →  bridge.setWeaponPlotSource("file:///...")
    ui.grollPlot   (QGraphicsView)      →  bridge.setGrollPlotSource("file:///...")
    ui.volumeSlider.value / 100.0       →  bridge.volume (0.0–1.0)
    ui.LoginInput / PasswordInput       →  bridge.setLoginValue / setPasswordValue
    ui.NicknameInput                    →  bridge.setNicknameValue
    ui.accountDataStasusDisplay.text    →  bridge.setAccountStatus(t)

Для отображения matplotlib-графиков в QML:
    import tempfile, os
    tmpf = tempfile.mktemp(suffix=".png")
    figure.savefig(tmpf, dpi=100, bbox_inches="tight",
                   facecolor="#0d0d18", edgecolor="none")
    bridge.setWeaponPlotSource("file:///" + tmpf.replace(os.sep, "/"))
"""

from PySide6.QtCore import QObject, Signal, Slot, Property


class MainWindowBridge(QObject):
    # ── Notify-сигналы (изменение свойств) ───────────────────────
    secondsFromUpdateChanged = Signal()
    updatesCountChanged      = Signal()
    podRollProgressChanged   = Signal()
    podRollMaxChanged        = Signal()
    grollProgressChanged     = Signal()
    grollMaxChanged          = Signal()
    programEnabledChanged    = Signal()
    currentStageChanged      = Signal()
    logsTextChanged          = Signal()
    statusLineChanged        = Signal()
    weaponListChanged        = Signal()
    statNamesChanged         = Signal()
    scheduleTextChanged      = Signal()
    podRollTextChanged       = Signal()
    dbWeaponsTextChanged     = Signal()
    cooldownValueChanged     = Signal()
    volumeChanged            = Signal()
    loginValueChanged        = Signal()
    passwordValueChanged     = Signal()
    nicknameValueChanged     = Signal()
    accountStatusChanged     = Signal()
    weaponPlotSourceChanged  = Signal()
    grollPlotSourceChanged   = Signal()

    # ── Сигналы действий (подключить в логике приложения) ────────
    toggleRequested            = Signal(bool)
    showLogsRequested          = Signal()
    buildWeaponPlotRequested   = Signal(str, int)        # weapon, mr_position
    showGrollRivensRequested   = Signal(str)
    buildGrollPlotRequested    = Signal(str, str, str, str, str)  # weapon + 4 stats
    saveScheduleRequested      = Signal(str)
    saveCooldownRequested      = Signal(str, str)        # weapon, seconds_str
    savePodRollRequested       = Signal(str)
    saveDbWeaponsRequested     = Signal(str)
    saveAccountDataRequested   = Signal(str, str, str)   # login, password, nickname
    verifyAccountDataRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sfu      = 0        # seconds_from_update
        self._upd      = 0        # updates_count
        self._pr_v     = 0        # podRoll progress value
        self._pr_m     = 100      # podRoll progress max
        self._gr_v     = 0        # groll progress value
        self._gr_m     = 100      # groll progress max
        self._enabled  = False
        self._stage    = "—"
        self._logs     = ""
        self._status   = ""
        self._weapons: list[str] = []
        self._stats:   list[str] = []
        self._sched    = ""
        self._podroll  = ""
        self._dbweap   = ""
        self._cdval    = ""
        self._volume   = 0.2
        self._login    = ""
        self._passwd   = ""
        self._nick     = ""
        self._acctst   = ""
        self._wplot    = ""
        self._gplot    = ""

    # ════════════════════════════════════════════════════════════
    #  Свойства (читаются из QML)
    # ════════════════════════════════════════════════════════════

    @Property(int,   notify=secondsFromUpdateChanged)
    def secondsFromUpdate(self): return self._sfu

    @Property(int,   notify=updatesCountChanged)
    def updatesCount(self): return self._upd

    @Property(int,   notify=podRollProgressChanged)
    def podRollProgress(self): return self._pr_v

    @Property(int,   notify=podRollMaxChanged)
    def podRollMax(self): return self._pr_m

    @Property(int,   notify=grollProgressChanged)
    def grollProgress(self): return self._gr_v

    @Property(int,   notify=grollMaxChanged)
    def grollMax(self): return self._gr_m

    @Property(bool,  notify=programEnabledChanged)
    def programEnabled(self): return self._enabled

    @Property(str,   notify=currentStageChanged)
    def currentStage(self): return self._stage

    @Property(str,   notify=logsTextChanged)
    def logsText(self): return self._logs

    @Property(str,   notify=statusLineChanged)
    def statusLine(self): return self._status

    @Property(list,  notify=weaponListChanged)
    def weaponList(self): return self._weapons

    @Property(list,  notify=statNamesChanged)
    def statNames(self): return self._stats

    @Property(str,   notify=scheduleTextChanged)
    def scheduleText(self): return self._sched

    @Property(str,   notify=podRollTextChanged)
    def podRollText(self): return self._podroll

    @Property(str,   notify=dbWeaponsTextChanged)
    def dbWeaponsText(self): return self._dbweap

    @Property(str,   notify=cooldownValueChanged)
    def cooldownValue(self): return self._cdval

    @Property(float, notify=volumeChanged)
    def volume(self): return self._volume

    @Property(str,   notify=loginValueChanged)
    def loginValue(self): return self._login

    @Property(str,   notify=passwordValueChanged)
    def passwordValue(self): return self._passwd

    @Property(str,   notify=nicknameValueChanged)
    def nicknameValue(self): return self._nick

    @Property(str,   notify=accountStatusChanged)
    def accountStatus(self): return self._acctst

    @Property(str,   notify=weaponPlotSourceChanged)
    def weaponPlotSource(self): return self._wplot

    @Property(str,   notify=grollPlotSourceChanged)
    def grollPlotSource(self): return self._gplot

    # ════════════════════════════════════════════════════════════
    #  Сеттеры (вызываются из Python-кода приложения)
    # ════════════════════════════════════════════════════════════

    def setSecondsFromUpdate(self, v: int):
        if self._sfu != v:
            self._sfu = v; self.secondsFromUpdateChanged.emit()

    def setUpdatesCount(self, v: int):
        if self._upd != v:
            self._upd = v; self.updatesCountChanged.emit()

    def setPodRollProgress(self, value: int, maximum: int = 100):
        if self._pr_v != value:
            self._pr_v = value; self.podRollProgressChanged.emit()
        if self._pr_m != maximum:
            self._pr_m = maximum; self.podRollMaxChanged.emit()

    def setGrollProgress(self, value: int, maximum: int = 100):
        if self._gr_v != value:
            self._gr_v = value; self.grollProgressChanged.emit()
        if self._gr_m != maximum:
            self._gr_m = maximum; self.grollMaxChanged.emit()

    def setProgramEnabled(self, v: bool):
        if self._enabled != v:
            self._enabled = v; self.programEnabledChanged.emit()

    def setCurrentStage(self, v: str):
        if self._stage != v:
            self._stage = v; self.currentStageChanged.emit()

    def appendLog(self, text: str):
        self._logs += text + "\n"; self.logsTextChanged.emit()

    def setLogsText(self, text: str):
        self._logs = text; self.logsTextChanged.emit()

    def clearLogs(self):
        self._logs = ""; self.logsTextChanged.emit()

    def setStatusLine(self, v: str):
        if self._status != v:
            self._status = v; self.statusLineChanged.emit()

    def setWeaponList(self, weapons: list):
        self._weapons = list(weapons); self.weaponListChanged.emit()

    def setStatNames(self, stats: list):
        self._stats = list(stats); self.statNamesChanged.emit()

    def setScheduleText(self, v: str):
        if self._sched != v:
            self._sched = v; self.scheduleTextChanged.emit()

    def setPodRollText(self, v: str):
        if self._podroll != v:
            self._podroll = v; self.podRollTextChanged.emit()

    def setDbWeaponsText(self, v: str):
        if self._dbweap != v:
            self._dbweap = v; self.dbWeaponsTextChanged.emit()

    def setCooldownValue(self, v: str):
        if self._cdval != v:
            self._cdval = v; self.cooldownValueChanged.emit()

    def setVolume(self, v: float):
        v = max(0.0, min(1.0, float(v)))
        if abs(self._volume - v) > 0.001:
            self._volume = v; self.volumeChanged.emit()

    def setLoginValue(self, v: str):
        if self._login != v:
            self._login = v; self.loginValueChanged.emit()

    def setPasswordValue(self, v: str):
        if self._passwd != v:
            self._passwd = v; self.passwordValueChanged.emit()

    def setNicknameValue(self, v: str):
        if self._nick != v:
            self._nick = v; self.nicknameValueChanged.emit()

    def setAccountStatus(self, v: str):
        if self._acctst != v:
            self._acctst = v; self.accountStatusChanged.emit()

    def setWeaponPlotSource(self, url: str):
        """Передайте file:///путь/к/графику.png после сохранения matplotlib-фигуры."""
        if self._wplot != url:
            self._wplot = url; self.weaponPlotSourceChanged.emit()

    def setGrollPlotSource(self, url: str):
        if self._gplot != url:
            self._gplot = url; self.grollPlotSourceChanged.emit()

    # ════════════════════════════════════════════════════════════
    #  Слоты (вызываются из QML)
    # ════════════════════════════════════════════════════════════

    @Slot(bool)
    def toggleProgram(self, enabled: bool):
        self.toggleRequested.emit(enabled)

    @Slot()
    def showLogs(self):
        self.showLogsRequested.emit()

    @Slot(str, int)
    def buildWeaponPlot(self, weapon: str, mr_pos: int):
        self.buildWeaponPlotRequested.emit(weapon, mr_pos)

    @Slot(str)
    def showGrollRivens(self, weapon: str):
        self.showGrollRivensRequested.emit(weapon)

    @Slot(str, str, str, str, str)
    def buildGrollPlot(self, weapon: str, s1: str, s2: str, s3: str, s4: str):
        self.buildGrollPlotRequested.emit(weapon, s1, s2, s3, s4)

    @Slot(str)
    def saveSchedule(self, text: str):
        self.saveScheduleRequested.emit(text)

    @Slot(str, str)
    def saveCooldown(self, weapon: str, value: str):
        self.saveCooldownRequested.emit(weapon, value)

    @Slot(str)
    def savePodRoll(self, text: str):
        self.savePodRollRequested.emit(text)

    @Slot(str)
    def saveDbWeapons(self, text: str):
        self.saveDbWeaponsRequested.emit(text)

    @Slot(float)
    def setVolumeFromQml(self, vol: float):
        self.setVolume(vol)

    @Slot(str, str, str)
    def saveAccountData(self, login: str, password: str, nickname: str):
        self.saveAccountDataRequested.emit(login, password, nickname)

    @Slot()
    def verifyAccountData(self):
        self.verifyAccountDataRequested.emit()
