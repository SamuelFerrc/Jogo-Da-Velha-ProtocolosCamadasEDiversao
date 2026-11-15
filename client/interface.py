
def criar_tabuleiro():
    """Cria um tabuleiro 3x3 inicialmente vazio."""
    return [
        ["", "", ""],
        ["", "", ""],
        ["", "", ""]
    ]


def exibir_tabuleiro(tabuleiro):
    """Exibe o tabuleiro no terminal."""

    print("\n")

    for linha in range(3):
        print(" " + " | ".join(
            celula if celula else " "
            for celula in tabuleiro[linha]
        ))

        if linha < 2:
            print("---+---+---")

    print("\n")

def solicitar_jogada():
    """Solicita ao jogador uma linha e uma coluna."""

    while True:
        try:
            linha = int(input("Escolha a linha (1 a 3): "))
            coluna = int(input("Escolha a coluna (1 a 3): "))

            if linha not in range(1, 4) or coluna not in range(1, 4):
                print("Posição inválida! Escolha números de 1 a 3.")
                continue

            return linha - 1, coluna - 1

        except ValueError:
            print("Digite apenas números inteiros.")
