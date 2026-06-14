import QtQuick
import QtQuick.Controls

Rectangle {

    width: ListView.view.width - 20
    height: 150

    radius: 12

    color: "#AA202020"

    border.color: "#80FFFFFF"

    Text {

        anchors.left: parent.left
        anchors.top: parent.top

        anchors.margins: 10

        color: "white"

        text:
            reason +
            "\nОружие: " + weapon +
            "\nЦена: " + price +
            "\nВладелец: " + owner
    }
}