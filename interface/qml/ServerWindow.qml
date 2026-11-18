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
    title: "TTTP/1 · Servidor · Jogo da Velha"
    color: theme.surfaceSoft

    DesignTokens { id: theme }

    Component.onCompleted: backend.startServer()
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
                            text: "S"
                            color: theme.textOnPrimary
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "TTTP/1  /  SERVIDOR AUTORITATIVO"
                        color: theme.primary
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }

                Text {
                    anchors.left: parent.left
                    anchors.top: brand.bottom
                    anchors.topMargin: 10
                    text: "Central de partidas"
                    color: theme.textOnDark
                    font.family: theme.sans
                    font.pixelSize: 32
                    font.weight: Font.Normal
                }
                Text {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    text: "Sessões, regras e transporte na mesma sequência observável."
                    color: theme.textOnDarkSoft
                    font.pixelSize: 12
                }

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    PillBadge {
                        text: backend.statusLabel
                        accent: true
                        width: 220
                    }
                    PillButton {
                        text: backend.actionLabel
                        primary: false
                        dark: true
                        implicitWidth: 132
                        onClicked: backend.toggleServer()
                    }
                }
            }

            LayerStrip {
                id: layerStrip
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                labels: ["Clientes / TCP", "shared.transport", "Aplicação servidor", "Lobby + Game"]
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    color: theme.canvas
                    radius: 18
                    border.width: 1
                    border.color: theme.hairline

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 18
                        anchors.rightMargin: 18
                        spacing: 0

                        Repeater {
                            model: [
                                { label: "SESSÕES CONECTADAS", value: backend.sessionCount },
                                { label: "NO LOBBY", value: backend.waitingCount },
                                { label: "PARTIDAS ATIVAS", value: backend.gameCount },
                                { label: "HANDSHAKE", value: backend.handshakeLabel }
                            ]
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: modelData.label
                                    color: theme.muted
                                    font.family: theme.sans
                                    font.pixelSize: 10
                                }
                                Text {
                                    text: modelData.value
                                    color: theme.ink
                                    font.family: theme.mono
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 16

                    Rectangle {
                        Layout.fillHeight: true
                        Layout.preferredWidth: 500
                        Layout.minimumWidth: 380
                        color: theme.canvas
                        radius: 22
                        border.width: 1
                        border.color: theme.hairline

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 9

                            Text {
                                text: "Sessões"
                                color: theme.ink
                                font.family: theme.sans
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: backend.addressLabel
                                color: theme.primary
                                font.family: theme.mono
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                Text { text: "CLIENTE"; color: theme.muted; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.preferredWidth: 96 }
                                Text { text: "ESTADO"; color: theme.muted; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                Text { text: "JOGO"; color: theme.muted; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.preferredWidth: 72 }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: theme.hairlineSoft }

                            ListView {
                                id: sessionsList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: backend.sessions
                                spacing: 0
                                clip: true

                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 42
                                    color: "transparent"
                                    border.width: 0
                                    RowLayout {
                                        anchors.fill: parent
                                        spacing: 8
                                        Rectangle {
                                            width: 28
                                            height: 28
                                            radius: 14
                                            color: modelData.game_id === "—" ? theme.surfaceStrong : theme.primary
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.client_id
                                                color: modelData.game_id === "—" ? theme.ink : theme.textOnPrimary
                                                font.pixelSize: 9
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                        Text {
                                            Layout.preferredWidth: 60
                                            text: modelData.client_id
                                            color: theme.ink
                                            font.family: theme.mono
                                            font.pixelSize: 11
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.state
                                            color: theme.body
                                            font.pixelSize: 11
                                        }
                                        Text {
                                            Layout.preferredWidth: 72
                                            text: modelData.game_id
                                            color: theme.ink
                                            font.family: theme.mono
                                            font.pixelSize: 11
                                        }
                                    }
                                    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: theme.hairlineSoft }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: sessionsList.count === 0
                                    text: "Aguardando conexões TCP"
                                    color: theme.muted
                                    font.pixelSize: 12
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 44
                                color: theme.surfaceDark
                                radius: 12
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 14
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: backend.gameSummary
                                    color: theme.textOnDark
                                    font.family: theme.mono
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: backend.explanation
                                color: theme.body
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    TraceTerminal {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 650
                        title: "Fluxo da requisição"
                        subtitle: "Transporte entrega; aplicação valida e decide."
                        events: backend.traceEvents
                    }
                }
            }
        }
    }
}
