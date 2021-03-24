import Pyro5.api
import threading
import time

NOME_DO_PROCESSO = "PEER_B"

OUTROS_PROCESSOS = ["PEER_A", "PEER_C"]

RECURSOS_COMPARTILHADOS =  {
    "RECURSO_A": "HELD", 
    "RECURSO_B": "RELEASED"
}

@Pyro5.api.expose
class StateChecker(object):
    def checkState(self, recurso):
        while RECURSOS_COMPARTILHADOS[recurso] == "HELD":
            time.sleep(1)
        return RECURSOS_COMPARTILHADOS[recurso]


def menu():
    print(f"MENU DO PROCESSO {NOME_DO_PROCESSO}")
    print("Com qual recurso compartilhado você gostaria de interagir?(A ou B)")
    recurso_escolhido = input()

    if recurso_escolhido != "A" and recurso_escolhido != "B":
        print("Opção selecionada não existe!!!")
        return
    recurso_escolhido = f"RECURSO_{recurso_escolhido}"

    print("1 - Checar status do recurso")
    print("2 - Liberar o recurso")
    print("3 - Requisitar o recurso")
    escolha = input()

    if escolha == "1":
        print(f"O status do {recurso_escolhido} é: {RECURSOS_COMPARTILHADOS[recurso_escolhido]}")
    elif escolha == "2":
        RECURSOS_COMPARTILHADOS[recurso_escolhido] = "RELEASED"
        print(f"O status do {recurso_escolhido} foi alterado.")
    elif escolha == "3":
        RECURSOS_COMPARTILHADOS[recurso_escolhido] = "WANTED"

        for processo in OUTROS_PROCESSOS:
            conexao = Pyro5.api.Proxy(f"PYRONAME:{processo}")
            timestamp = time.time()
            print(conexao.checkStatus(recurso_escolhido)) 

    else:
        print("Opção selecionada não existe!!!")

def threadFunction(daemon):
    daemon.requestLoop()                   # start the event loop of the server to wait for calls

def main():
    # Cria um Pyro daemon
    daemon = Pyro5.server.Daemon()         
    #Encontra o servidor de nomes
    ns = Pyro5.api.locate_ns()
    uri = daemon.register(StateChecker)   # register the greeting maker as a Pyro object
    ns.register(NOME_DO_PROCESSO, uri)   # register the object with a name in the name server

    while True:
        x = threading.Thread(target=threadFunction, args=(daemon, ))
        x.start()
        menu()
    #daemon.requestLoop()                   # start the event loop of the server to wait for calls

if __name__ == "__main__":
    main()