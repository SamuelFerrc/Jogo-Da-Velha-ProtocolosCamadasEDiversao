import QtQuick

Rectangle {
    id: root
    property alias text: label.text
    property bool accent: false
    property bool dark: false
    implicitWidth: Math.max(94, label.implicitWidth + 28)
    implicitHeight: 30
    radius: height / 2
    color: accent ? theme.primary : (dark ? theme.surfaceDark : theme.surfaceStrong)

    DesignTokens { id: theme }

    Text {
        id: label
        anchors.centerIn: parent
        color: root.accent || root.dark ? theme.textOnDark : theme.ink
        font.family: theme.sans
        font.pixelSize: 11
        font.weight: Font.DemiBold
    }
}
