import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property var labels: []
    height: 48
    color: theme.surfaceDark

    DesignTokens { id: theme }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        spacing: 8

        Repeater {
            model: root.labels.length
            delegate: RowLayout {
                required property int index
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    radius: 2
                    color: theme.surfaceDarkElevated
                    Text {
                        anchors.centerIn: parent
                        text: root.labels[index].toUpperCase()
                        color: theme.textOnDark
                        font.family: theme.sans
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }

                Text {
                    visible: index < root.labels.length - 1
                    text: index >= root.labels.length - 1 ? ""
                          : (root.labels[index].indexOf("TCP") >= 0
                             || root.labels[index + 1].indexOf("TCP") >= 0 ? "⇄" : "→")
                    color: theme.primary
                    font.family: theme.sans
                    font.pixelSize: 16
                }
            }
        }
    }
}
