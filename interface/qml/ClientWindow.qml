pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window
    width: 1240
    height: 820
    minimumWidth: 1000
    minimumHeight: 720
    visible: true
    title: "TTTP/1 · Cliente · Jogo da Velha"
    color: theme.surfaceSoft

    DesignTokens { id: theme }

    Component.onCompleted: {
        backend.connectToServer()
        backend.startConsole()
    }
    onClosing: backend.shutdown()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 196
            color: theme.surfaceDark

            Item {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: layerStrip.top
                anchors.leftMargin: 28
                anchors.rightMargin: 28
                anchors.topMargin: 16
                anchors.bottomMargin: 14

                Row {
                    id: brand
                    anchors.left: parent.left
                    anchors.top: parent.top
                    spacing: 10

                    Rectangle {
                        width: 34
                        height: 34
                        radius: 17
                        color: theme.primary
                        Text {
                            anchors.centerIn: parent
                            text: "T"
                            color: theme.textOnPrimary
                            font.family: theme.sans
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "TTTP/1  /  CLIENTE"
                        color: theme.primary
                        font.family: theme.sans
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }

                Text {
                    anchors.left: parent.left
                    anchors.top: brand.bottom
                    anchors.topMargin: 10
                    text: "Jogo da Velha"
                    color: theme.textOnDark
                    font.family: theme.sans
                    font.pixelSize: 32
                    font.weight: Font.Normal
                }
                Text {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    text: "Jogue enquanto cada mensagem percorre as camadas reais."
                    color: theme.textOnDarkSoft
                    font.family: theme.sans
                    font.pixelSize: 12
                }

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    PillBadge {
                        text: backend.phaseLabel
                        accent: true
                        width: 150
                    }
                    PillButton {
                        text: "Desconectar"
                        primary: false
                        dark: true
                        enabled: backend.connected
                        implicitWidth: 124
                        onClicked: backend.disconnectFromServer()
                    }
                }
            }

            LayerStrip {
                id: layerStrip
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                labels: ["Interface", "Aplicação cliente", "shared.transport", "TCP / servidor"]
            }
        }

        Item {
            id: workspace
            objectName: "workspace"
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                id: mainLayout
                objectName: "mainLayout"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: terminalDrawer.top
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.topMargin: 20
                anchors.bottomMargin: 14
                spacing: 16

                Rectangle {
                    id: gameCard
                    objectName: "gameCard"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    Layout.maximumHeight: mainLayout.height
                    Layout.preferredWidth: 690
                    color: theme.canvas
                    radius: 22
                    border.width: 1
                    border.color: theme.hairline

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    text: backend.gameTitle
                                    color: theme.ink
                                    font.family: theme.sans
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    text: "Tabuleiro oficial recebido do servidor."
                                    color: theme.muted
                                    font.family: theme.sans
                                    font.pixelSize: 11
                                }
                            }
                            PillBadge { text: backend.turnLabel; implicitWidth: 106 }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 22
                            spacing: 7
                            Rectangle { width: 8; height: 8; radius: 4; color: theme.primary }
                            Text {
                                Layout.fillWidth: true
                                text: backend.notice
                                color: theme.body
                                font.family: theme.sans
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        Item {
                            id: boardArea
                            objectName: "boardArea"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 0

                            Grid {
                                id: board
                                objectName: "officialBoard"
                                columns: 3
                                spacing: 10
                                width: Math.max(0, Math.min(430, parent.width, parent.height))
                                height: width
                                anchors.centerIn: parent

                                Repeater {
                                    model: 9
                                    delegate: FocusScope {
                                        id: cellDelegate
                                        required property int index
                                        property int rowIndex: Math.floor(index / 3)
                                        property int columnIndex: index % 3
                                        property string markValue: backend.stateTick >= 0
                                                                  ? backend.cellAt(rowIndex, columnIndex) : ""
                                        property bool playable: backend.stateTick >= 0
                                                                && backend.canPlay(rowIndex, columnIndex)
                                        width: (board.width - board.spacing * 2) / 3
                                        height: width
                                        activeFocusOnTab: playable

                                        Rectangle {
                                            anchors.fill: parent
                                            radius: Math.min(18, cellDelegate.width * 0.14)
                                            color: cellPointer.containsMouse && cellDelegate.playable
                                                   ? theme.surfaceStrong : theme.surfaceSoft
                                            border.width: cellDelegate.activeFocus ? 2 : 1
                                            border.color: cellDelegate.activeFocus || cellDelegate.playable
                                                          ? theme.primary : theme.hairline
                                            Behavior on color { ColorAnimation { duration: 100 } }

                                            Text {
                                                anchors.centerIn: parent
                                                text: cellDelegate.markValue
                                                color: text === "X" ? theme.primary : theme.ink
                                                font.family: theme.sans
                                                font.pixelSize: Math.min(52, parent.width * 0.38)
                                                font.weight: Font.Normal
                                            }
                                            MouseArea {
                                                id: cellPointer
                                                anchors.fill: parent
                                                enabled: cellDelegate.playable
                                                hoverEnabled: true
                                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                onClicked: {
                                                    cellDelegate.forceActiveFocus()
                                                    backend.play(cellDelegate.rowIndex, cellDelegate.columnIndex)
                                                }
                                            }
                                        }
                                        Keys.onReturnPressed: if (playable) backend.play(rowIndex, columnIndex)
                                        Keys.onSpacePressed: if (playable) backend.play(rowIndex, columnIndex)
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text {
                                Layout.fillWidth: true
                                text: "O clique gera MOVE; a casa só muda após BOARD."
                                color: theme.muted
                                font.family: theme.sans
                                font.pixelSize: 11
                            }
                            PillBadge { text: "REVISÃO " + backend.revisionLabel; implicitWidth: 108 }
                        }
                    }
                }

                ColumnLayout {
                    id: sidebar
                    objectName: "sidebar"
                    Layout.fillHeight: true
                    Layout.preferredWidth: 300
                    Layout.minimumWidth: 250
                    Layout.minimumHeight: 0
                    Layout.maximumHeight: mainLayout.height
                    spacing: 12

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 198
                        color: theme.canvas
                        radius: 18
                        border.width: 1
                        border.color: theme.hairline

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 7
                            Text {
                                text: "Conexão"
                                color: theme.ink
                                font.family: theme.sans
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: "Socket TCP direto"
                                color: theme.muted
                                font.family: theme.sans
                                font.pixelSize: 11
                            }

                            GridLayout {
                                visible: !backend.connected
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 8
                                rowSpacing: 4
                                Text { text: "Host"; color: theme.muted; font.pixelSize: 10 }
                                Text { text: "Porta"; color: theme.muted; font.pixelSize: 10 }
                                TextField {
                                    Layout.fillWidth: true
                                    text: backend.host
                                    color: theme.ink
                                    selectByMouse: true
                                    onTextEdited: backend.host = text
                                    background: Rectangle {
                                        color: theme.canvas
                                        radius: 12
                                        border.width: parent.activeFocus ? 2 : 1
                                        border.color: parent.activeFocus ? theme.primary : theme.hairline
                                    }
                                }
                                TextField {
                                    Layout.preferredWidth: 82
                                    text: backend.port
                                    color: theme.ink
                                    selectByMouse: true
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    onTextEdited: backend.port = text
                                    background: Rectangle {
                                        color: theme.canvas
                                        radius: 12
                                        border.width: parent.activeFocus ? 2 : 1
                                        border.color: parent.activeFocus ? theme.primary : theme.hairline
                                    }
                                }
                            }

                            ColumnLayout {
                                visible: backend.connected
                                Layout.fillWidth: true
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Host"; color: theme.muted; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: backend.host; color: theme.ink; font.family: theme.mono; font.pixelSize: 11; font.weight: Font.DemiBold }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Porta"; color: theme.muted; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: backend.port; color: theme.ink; font.family: theme.mono; font.pixelSize: 11; font.weight: Font.DemiBold }
                                }
                                RowLayout {
                                    spacing: 5
                                    Rectangle { width: 7; height: 7; radius: 4; color: theme.primary }
                                    Text { text: backend.connectionLabel; color: theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                }
                            }

                            Item { Layout.fillHeight: true }
                            PillButton {
                                visible: !backend.connected
                                text: "Conectar"
                                implicitWidth: 116
                                onClicked: backend.connectToServer()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 174
                        color: theme.canvas
                        radius: 18
                        border.width: 1
                        border.color: theme.hairline

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Text { text: "Sessão"; color: theme.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                            Repeater {
                                model: [
                                    { label: "Sua marca", value: backend.mark },
                                    { label: "Game ID", value: backend.gameId },
                                    { label: "Revisão", value: backend.revisionLabel }
                                ]
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Text { text: modelData.label; color: theme.muted; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: modelData.value; color: theme.ink; font.family: theme.mono; font.pixelSize: 11; font.weight: Font.DemiBold }
                                }
                            }
                            Item { Layout.fillHeight: true }
                            PillButton {
                                visible: backend.canPlayAgain
                                text: "Jogar novamente"
                                implicitWidth: 154
                                onClicked: backend.playAgain()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 122
                        color: theme.authoritySoft
                        radius: 18
                        border.width: 1
                        border.color: theme.hairline

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 8
                            Text {
                                text: "Estado autoritativo"
                                color: theme.primaryActive
                                font.family: theme.sans
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: "O cliente solicita a jogada. O servidor valida turno, posição e célula e devolve o novo tabuleiro oficial."
                                color: theme.body
                                font.family: theme.sans
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                verticalAlignment: Text.AlignTop
                            }
                        }
                    }
                }
            }

            Item { id: dragProxy; y: 0 }

            Rectangle {
                id: terminalDrawer
                objectName: "terminalDrawer"
                property bool open: false
                readonly property real collapsedHeight: 58
                readonly property real minimumMainHeight: 360
                readonly property real expandedHeight: Math.min(
                    330,
                    Math.max(collapsedHeight, workspace.height - minimumMainHeight)
                )
                property real restingHeight: open ? expandedHeight : collapsedHeight
                property real dragDistance: dragProxy.y
                height: handleArea.drag.active
                        ? Math.max(collapsedHeight, Math.min(expandedHeight, restingHeight - dragDistance))
                        : restingHeight
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.bottomMargin: 16
                color: theme.surfaceDarkElevated
                radius: 20
                z: 100
                clip: true
                border.width: 1
                border.color: "#292c31"

                Behavior on height {
                    enabled: !handleArea.drag.active
                    NumberAnimation {
                        duration: terminalDrawer.open ? 340 : 250
                        easing.type: terminalDrawer.open ? Easing.OutCubic : Easing.InOutCubic
                    }
                }

                Item {
                    id: drawerHandle
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: terminalDrawer.collapsedHeight

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3
                        Repeater {
                            model: 3
                            Rectangle { width: 18; height: 2; radius: 1; color: "#666b74" }
                        }
                    }
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 54
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text { text: "Terminal TTTP/1"; color: theme.textOnDark; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text {
                            text: terminalDrawer.open
                                  ? "Puxe para baixo ou clique para devolver espaço ao jogo"
                                  : "Puxe para cima; o jogo se ajusta sem deformar o tabuleiro"
                            color: theme.textOnDarkSoft
                            font.pixelSize: 10
                        }
                    }
                    PillBadge {
                        anchors.right: arrow.left
                        anchors.rightMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: "AO VIVO"
                        accent: true
                        implicitWidth: 78
                    }
                    Text {
                        id: arrow
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        anchors.verticalCenter: parent.verticalCenter
                        text: terminalDrawer.open ? "⌄" : "⌃"
                        color: theme.textOnDarkSoft
                        font.pixelSize: 18
                    }

                    MouseArea {
                        id: handleArea
                        anchors.fill: parent
                        cursorShape: Qt.SizeVerCursor
                        drag.target: dragProxy
                        drag.axis: Drag.YAxis
                        drag.minimumY: -(terminalDrawer.expandedHeight - terminalDrawer.collapsedHeight)
                        drag.maximumY: terminalDrawer.expandedHeight - terminalDrawer.collapsedHeight
                        preventStealing: true
                        onPressed: dragProxy.y = 0
                        onReleased: {
                            const distance = dragProxy.y
                            if (distance < -34)
                                terminalDrawer.open = true
                            else if (distance > 34)
                                terminalDrawer.open = false
                            else if (Math.abs(distance) < 8)
                                terminalDrawer.open = !terminalDrawer.open
                            dragProxy.y = 0
                        }
                    }
                }

                TraceTerminal {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: drawerHandle.bottom
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    anchors.topMargin: 0
                    showHeader: false
                    events: backend.traceEvents
                    opacity: Math.max(0, Math.min(1,
                             (terminalDrawer.height - terminalDrawer.collapsedHeight) / 90))
                    Behavior on opacity { NumberAnimation { duration: 180 } }
                }
            }
        }
    }
}
