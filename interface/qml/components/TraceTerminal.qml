import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property var events: []
    property string title: "Fluxo da requisição"
    property string subtitle: "Transporte entrega; aplicação valida e decide."
    property bool showHeader: true
    color: theme.surfaceDarkElevated
    radius: 22
    clip: true

    DesignTokens { id: theme }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            visible: root.showHeader
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 52 : 0
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: root.title
                    color: theme.textOnDark
                    font.family: theme.sans
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }
                Text {
                    text: root.subtitle
                    color: theme.textOnDarkSoft
                    font.family: theme.sans
                    font.pixelSize: 11
                }
            }
            PillBadge { text: "JSONL · UTF-8"; dark: true; implicitWidth: 124 }
            PillBadge { text: "LF / 4096 B"; accent: true; implicitWidth: 108 }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: theme.surfaceDark
            radius: 10
            clip: true

            ListView {
                id: eventList
                anchors.fill: parent
                anchors.margins: 10
                model: root.events
                spacing: 0
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                onCountChanged: Qt.callLater(positionViewAtEnd)

                delegate: Item {
                    required property var modelData
                    width: ListView.view.width
                    height: eventColumn.implicitHeight + 18

                    Column {
                        id: eventColumn
                        width: parent.width - 6
                        spacing: 3
                        topPadding: 8

                        Text {
                            width: parent.width
                            text: "[" + modelData.time + "] " + modelData.layer + " "
                                  + modelData.direction + "  " + modelData.action
                                  + (modelData.messageType ? " · " + modelData.messageType : "")
                                  + (modelData.peer ? " · " + modelData.peer : "")
                            color: modelData.application ? "#78a7ff" : theme.textOnDarkSoft
                            font.family: theme.mono
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            wrapMode: Text.Wrap
                        }
                        Text {
                            visible: modelData.detail.length > 0
                            width: parent.width
                            text: modelData.detail
                            color: modelData.error ? "#ff7b86" : theme.textOnDarkSoft
                            font.family: theme.mono
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                        }
                        Text {
                            visible: modelData.metrics.length > 0
                            width: parent.width
                            text: modelData.metrics
                            color: theme.textOnDarkSoft
                            font.family: theme.mono
                            font.pixelSize: 10
                        }
                        Text {
                            visible: modelData.payload.length > 0
                            width: parent.width
                            text: modelData.payload
                            color: "#d8e4ff"
                            font.family: theme.mono
                            font.pixelSize: 10
                            wrapMode: Text.WrapAnywhere
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: "#25282d"
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: eventList.count === 0
                    text: "Os eventos reais aparecerão aqui."
                    color: theme.textOnDarkSoft
                    font.family: theme.sans
                    font.pixelSize: 12
                }
            }
        }
    }
}
