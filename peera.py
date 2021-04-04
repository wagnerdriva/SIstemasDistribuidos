import Pyro5.api
import threading
import time

NOME_DO_PROCESSO = "PEER_A"

OUTROS_PROCESSOS = ["PEER_B", "PEER_C"]

RECURSOS_COMPARTILHADOS =  {
    "RECURSO_A": {
        "status": "RELEASED",
        "timestamp": None,
        "fila": list(),
        "aguardando_retorno": list() # Problema de quando o mesmo processo requisita o mesmo recurso depois de outro processo ter requisitado
    }, 
    "RECURSO_B": {
        "status": "RELEASED",
        "timestamp": None,
        "fila": list(),
        "aguardando_retorno": list() # Problema de quando o mesmo processo requisita o mesmo recurso depois de outro processo ter requisitado
    }
}

@Pyro5.api.expose
class StateChecker(object):
    def receberInscricao(self, recurso, timestamp, processo):
        if RECURSOS_COMPARTILHADOS[recurso]["status"] == "RELEASED":
            return "RECURSO_LIVRE"
        elif (RECURSOS_COMPARTILHADOS[recurso]["status"] == "WANTED" and 
              RECURSOS_COMPARTILHADOS[recurso]["timestamp"] > timestamp):
            return "RECURSO_LIVRE"
        else:
            RECURSOS_COMPARTILHADOS[recurso]["fila"].append(processo)
            return "RECURSO_OCUPADO"

    def enviarNotificacao(self, recurso, processo):
        # Removemos o processo da lista em que estamos aguardando a resposta
        RECURSOS_COMPARTILHADOS[recurso]["aguardando_retorno"].remove(processo)

        # Se a lsita estiver vazia, quer dizer que recebemos todas as respostas e 
        # que podemos utilizar o processo
        if len(RECURSOS_COMPARTILHADOS[recurso]["aguardando_retorno"]) == 0:
            RECURSOS_COMPARTILHADOS[recurso]["status"] = "HELD"


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
        # Mudamos o status do recurso para RELEASED
        RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "RELEASED"
        
        processos_notificados = list()
        #Para cada processo que estava na fila para usar esse recurso
        for processo in RECURSOS_COMPARTILHADOS[recurso_escolhido]["fila"]:
            #Nos conectamos e enviamos a notificacao de que o processo está livre agora
            conexao = Pyro5.api.Proxy(f"PYRONAME:{processo}")
            conexao.enviarNotificacao(recurso_escolhido, NOME_DO_PROCESSO)

            # Removemos o pedido da fila
            processos_notificados.append(processo)

        for processo in processos_notificados:
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["fila"].remove(processo)

        # Printamos para o usuario que o recurso foi liberado
        print(f"O status do {recurso_escolhido} foi alterado.")
    elif escolha == "3":
        # Mudamos o status do recurso para WANTED
        RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "WANTED"
        # Guardamos o timestamp em que o recurso foi solicitado
        timestamp = time.time()
        RECURSOS_COMPARTILHADOS[recurso_escolhido]["timestamp"] = timestamp

        # Enviamos para todos os outros processos que temos o interesse de utilizar o recurso
        for processo in OUTROS_PROCESSOS:
            conexao = Pyro5.api.Proxy(f"PYRONAME:{processo}")
            resposta = conexao.receberInscricao(recurso_escolhido, timestamp, NOME_DO_PROCESSO)

            if resposta == "RECURSO_OCUPADO":
                RECURSOS_COMPARTILHADOS[recurso_escolhido]["aguardando_retorno"].append(processo)
        
        # Se a lista estiver vazia, quer dizer que recebemos todas as respostas e 
        # que podemos utilizar o processo
        if len(RECURSOS_COMPARTILHADOS[recurso_escolhido]["aguardando_retorno"]) == 0:
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "HELD"

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

if __name__ == "__main__":
    main()