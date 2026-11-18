import QtQuick

FocusScope {
    id: root
    property alias text: label.text
    property bool primary: true
    property bool dark: false
    signal clicked()
    implicitWidth: 144
    implicitHeight: 44
    activeFocusOnTab: true
    scale: pointer.pressed ? 0.985 : 1

    DesignTokens { id: theme }

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: {
            if (!root.enabled)
                return root.primary ? theme.primaryDisabled : (root.dark ? "#292c31" : theme.surfaceStrong)
            if (root.primary)
                return pointer.containsMouse ? theme.primaryActive : theme.primary
            if (root.dark)
                return pointer.containsMouse ? "#25282d" : theme.surfaceDarkElevated
            return pointer.containsMouse ? theme.hairline : theme.surfaceStrong
        }
        border.width: root.activeFocus ? 2 : 0
        border.color: root.primary ? theme.textOnPrimary : theme.primary

        Behavior on color { ColorAnimation { duration: 110 } }
    }

    Text {
        id: label
        anchors.centerIn: parent
        color: root.primary || root.dark ? theme.textOnDark : (root.enabled ? theme.ink : theme.muted)
        font.family: theme.sans
        font.pixelSize: 13
        font.weight: Font.DemiBold
    }

    MouseArea {
        id: pointer
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    Keys.onReturnPressed: if (root.enabled) root.clicked()
    Keys.onSpacePressed: if (root.enabled) root.clicked()
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
}
