// RivenAlertDelegate.qml
// Делегат одной карточки ривена. Заменяет RivenAlertWidget.
//
// required property var alertItem — имя совпадает с ролью "alertItem"
// в RivenListModel.roleNames(), поэтому ListView заполняет её автоматически.
// Везде используется ?. (optional chaining, Qt 6 / Qt 5.15+) на случай
// промежуточных состояний первичного рендера.

import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    required property var alertItem

    width:  parent ? parent.width : 500
    height: card.implicitHeight + 16

    color:        Qt.rgba(0.12, 0.12, 0.19, 0.82)   // 82% — текст читаем, видео просвечивает
    radius:       7
    border.color: Qt.rgba(0.22, 0.22, 0.36, 0.9)
    border.width: 1

    // ── Переиспользуемая кнопка (inline-компонент, Qt 5.15+) ─────
    component AlertButton: Rectangle {
        id: btn
        property alias text:        label.text
        property color normalColor: "#2e2e4a"
        property color hoverColor:  "#42426a"
        property color textColor:   "#cdd0e0"
        signal clicked()

        implicitWidth:  label.implicitWidth + 18
        implicitHeight: 26
        radius:         4
        color:          area.containsMouse ? hoverColor : normalColor

        Behavior on color { ColorAnimation { duration: 80 } }

        Text {
            id: label
            anchors.centerIn: parent
            color:            btn.textColor
            font.family:      "Segoe UI, Arial"
            font.pixelSize:   11
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape:  Qt.PointingHandCursor
            onClicked:    btn.clicked()
        }
    }

    // ── Основной контент ─────────────────────────────────────────
    ColumnLayout {
        id: card
        anchors {
            left:    parent.left
            right:   parent.right
            top:     parent.top
            margins: 10
        }
        spacing: 5

        // ── Основной текст ───────────────────────────────────────
        Text {
            Layout.fillWidth: true
            text:       root.alertItem?.mainHtml  ?? ""
            textFormat: Text.RichText
            wrapMode:   Text.Wrap
            color:      "#d0d3e0"
            font.family:    "Segoe UI, Arial"
            font.pixelSize: 12
            lineHeight:     1.25
        }

        // ── Строка статов (только для good stats / manual / sold) ─
        Text {
            Layout.fillWidth: true
            visible:    root.alertItem?.showStats  ?? false
            text:       root.alertItem?.statsHtml  ?? ""
            textFormat: Text.RichText
            wrapMode:   Text.Wrap
            color:      "#d0d3e0"
            font.family:    "Segoe UI, Arial"
            font.pixelSize: 12
        }

        // ── Кнопки ───────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: 4

            AlertButton {
                text:      "📋 Владелец"
                onClicked: root.alertItem?.copyOwner()
            }
            AlertButton {
                text:      "📋 Сообщение"
                onClicked: root.alertItem?.copyMessage()
            }
            AlertButton {
                text:      "🔗 Аукцион"
                onClicked: root.alertItem?.openAuction()
            }
            AlertButton {
                visible:   root.alertItem?.showPlot    ?? false
                text:      "📋 График"
                onClicked: root.alertItem?.requestPlot()
            }
            AlertButton {
                visible:   root.alertItem?.dismissable ?? false
                text:      "📋 Не показывать"
                onClicked: root.alertItem?.requestSave()
            }

            Item { Layout.fillWidth: true }

            AlertButton {
                text:        "❌ Удалить"
                normalColor: "#3e1a1a"
                hoverColor:  "#5e2a2a"
                textColor:   "#ffaaaa"
                onClicked:   root.alertItem?.requestDelete()
            }
        }
    }
}
