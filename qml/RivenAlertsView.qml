// RivenAlertsView.qml
// Корневой контейнер. Получает модель через контекстное свойство rivenModel.
//
// Источники задаются из Python после загрузки QML:
//   qml_widget.rootObject().setProperty("videoSource",
//       QUrl.fromLocalFile("path/to/video.mp4"))
//   qml_widget.rootObject().setProperty("imageSource",
//       QUrl.fromLocalFile("path/to/image.png"))

import QtQuick
import QtQuick.Controls
import QtMultimedia

Rectangle {
    id: root
    color: "#12121e"

    property url videoSource: ""
    property url imageSource: ""

    // ── Слой 0: изображение (фон по умолчанию) ───────────────────
    Image {
        id: bgImage
        anchors.fill: parent
        source:       root.imageSource
        fillMode:     Image.PreserveAspectCrop
        z:            0
    }

    // ── Слой 1: видео (перекрывает изображение во время воспроизведения) ──
    VideoOutput {
        id: videoOut
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
        z:            1

        // Плавно появляется при старте и исчезает при остановке,
        // открывая изображение под собой
        opacity: player.playbackState === MediaPlayer.PlayingState ? 1.0 : 0.0
        Behavior on opacity {
            NumberAnimation { duration: 400; easing.type: Easing.InOutQuad }
        }
    }

    MediaPlayer {
        id: player
        source:      root.videoSource
        videoOutput: videoOut
        loops:       MediaPlayer.Once
        audioOutput: AudioOutput {
                    id: audioOut
                    volume: 0.2  // Initial volume (0.0 = mute, 1.0 = full volume)
                }
    }

    // ── Слой 2: список алертов поверх всего ──────────────────────
    ListView {
        id: listView
        anchors {
            fill:    parent
            margins: 6
        }
        model:   rivenModel
        spacing: 6
        clip:    true
        z:       2

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 200 }
            NumberAnimation { property: "y";       from: -24;       duration: 200 }
        }
        remove: Transition {
            NumberAnimation { property: "opacity"; to: 0; duration: 150 }
        }
        displaced: Transition {
            NumberAnimation { properties: "y"; duration: 180; easing.type: Easing.OutCubic }
        }

        delegate: RivenAlertDelegate {
            width: listView.width
        }
    }

    // Adjust volume at runtime (e.g., from a slider, button, or function)
    function changeVolume(newVolume) {
        audioOut.volume = newVolume; // Expects a value between 0.0 and 1.0
    }

    // ── Триггер видео при новом алерте ────────────────────────────
    Connections {
        target: rivenModel
        function onAlertAdded() {
            player.stop()
            player.play()
        }
    }
}
