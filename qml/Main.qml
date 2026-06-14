import QtQuick
import QtQuick.Controls
import QtMultimedia

ApplicationWindow {

    visible: true

    width: 1200
    height: 900

    MediaPlayer {
        id: player
        source: "file:///C:/amyfiles/projects/rivenendo/videos/robot22.mp4"
        videoOutput: videoOutput
    }

    VideoOutput {
        id: videoOutput
        anchors.fill: parent
    }

    Rectangle {
        anchors.fill: parent

        color: "#20000000"

        z: 1
    }

    ListView {

        id: alertList

        anchors.fill: parent

        model: rivenModel

        spacing: 8

        z: 2

        delegate: RivenDelegate {}
    }
}