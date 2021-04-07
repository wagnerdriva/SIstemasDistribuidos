from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 
from Crypto import Random
import Pyro5.api
import threading
import time

from base64 import b64decode

# Randon seed (Numero aleatorio) para geração das chaves
random_seed = Random.new().read
# Gera o par de chaves
keyPair = RSA.generate(1024, random_seed)
# Chave publica
pubKey = keyPair.publickey()

# Numero de processos localizados
countLocatedProcess = 0

NOME_DO_PROCESSO = "PEER_A"

OUTROS_PROCESSOS = {
    "PEER_B": {
        "chavePublica": None,
        "objetoRemoto": None,
    },
    "PEER_C": {
        "chavePublica": None,
        "objetoRemoto": None,
    }
}

RECURSOS_COMPARTILHADOS =  {
    "RECURSO_A": {
        "status": "RELEASED",
        "timestamp": None,
        "fila": list(),
        "aguardando_retorno": list() 
    }, 
    "RECURSO_B": {
        "status": "RELEASED",
        "timestamp": None,
        "fila": list(),
        "aguardando_retorno": list()
    }
}

@Pyro5.api.expose
class ObjetoRemoto(object):
    def receberInscricao(self, digitalSignData, data):
        # Gera o hash para verificacao com assinatura digital
        chavePublica = b64decode(str(OUTROS_PROCESSOS[data["nomeDoProcesso"]]["chavePublica"]["data"]))
        rsakey = RSA.importKey(chavePublica)
        dataHash = SHA256.new(str(data).encode('utf-8')).digest()


        # Verifica a autenticidade dos dados, utilizando a chave publica e a assinatura digital recebida
        if(rsakey.verify(dataHash, digitalSignData)):
            # Se não estivermos usando o recurso compartilhado, ja respondemos
            # que o recurso esta livre
            if RECURSOS_COMPARTILHADOS[data["recurso"]]["status"] == "RELEASED":
                return "RECURSO_LIVRE"
            # Se o recurso estiver como WANTED, mas o timestamp do processo requisitado for menor,
            # também respondemos que o recurso pode ser utilizado
            elif (RECURSOS_COMPARTILHADOS[data["recurso"]]["status"] == "WANTED" and 
                RECURSOS_COMPARTILHADOS[data["recurso"]]["timestamp"] > data["timestamp"]):
                return "RECURSO_LIVRE"
            # Caso contrario, estamos utilizando o recurso ou estamos a frente na fila
            # então adicionamos o processo na nossa fila para avisa-lo quando o recurso 
            # estiver disponivel
            else:
                RECURSOS_COMPARTILHADOS[data["recurso"]]["fila"].append(data["nomeDoProcesso"])
                return "RECURSO_OCUPADO"
        else:
            return "DADOS_CORROMPIDOS"

    def enviarNotificacao(self, digitalSignData, data):
        global OUTROS_PROCESSOS

        # Gera o hash para verificacao com assinatura digital
        chavePublica = b64decode(str(OUTROS_PROCESSOS[data["nomeDoProcesso"]]["chavePublica"]["data"]))
        rsakey = RSA.importKey(chavePublica)
        dataHash = SHA256.new(str(data).encode('utf-8')).digest()

        # Verifica a autenticidade dos dados, utilizando a chave publica e a assinatura digital recebida
        if(rsakey.verify(dataHash, digitalSignData)):
            # Removemos o processo da lista em que estamos aguardando a resposta
            
            RECURSOS_COMPARTILHADOS[data["recurso"]]["aguardando_retorno"].remove(data["nomeDoProcesso"])

            # Se a lsita estiver vazia, quer dizer que recebemos todas as respostas e 
            # que podemos utilizar o processo
            # if 0 == -1
            if len(RECURSOS_COMPARTILHADOS[data["recurso"]]["aguardando_retorno"]) == 0:
                RECURSOS_COMPARTILHADOS[data["recurso"]]["status"] = "HELD"
    
    # Retorna a chave publica do processo
    def getPubKey(self):
        return pubKey.exportKey('DER')


def menu():
    # Esperando todos processos entrarem no ar
    if countLocatedProcess != len(OUTROS_PROCESSOS.items()):
        time.sleep(0.300)
        return

    # Printa as opções do menu
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
        # Se o recurso estiver sendo utilizado
        if RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] == "HELD":
            # Mudamos o status do recurso para RELEASED
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "RELEASED"
            
            processos_notificados = list()
            #Para cada processo que estava na fila para usar esse recurso
            for processo in RECURSOS_COMPARTILHADOS[recurso_escolhido]["fila"]:

                # Dicionario com os dados a serem enviados
                data = {
                    "recurso": recurso_escolhido,
                    "nomeDoProcesso": NOME_DO_PROCESSO
                }
                # Gera um hash com os dados, após serem transformados em string
                dataHash = SHA256.new(str(data).encode('utf-8')).digest()
                # Assinar o hash
                digitalSignData = keyPair.sign(dataHash, '')

                OUTROS_PROCESSOS[processo]["objetoRemoto"] = Pyro5.api.Proxy(f"PYRONAME:{processo}")
                OUTROS_PROCESSOS[processo]["objetoRemoto"].enviarNotificacao(digitalSignData, data)

                # Removemos o pedido da fila
                processos_notificados.append(processo)

            # Tiramos os processos notificados da fila
            for processo in processos_notificados:
                RECURSOS_COMPARTILHADOS[recurso_escolhido]["fila"].remove(processo)

            # Printamos para o usuario que o recurso foi liberado
            print(f"O status do {recurso_escolhido} foi alterado.")
        else:
            print(f"O {recurso_escolhido} não está em uso por esse processo para ser liberado")
    elif escolha == "3":
        # Verifica se o recurso já não está em uso
        if (RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] != "WANTED" and
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] != "HELD"):

            # Mudamos o status do recurso para WANTED
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "WANTED"
            # Guardamos o timestamp em que o recurso foi solicitado
            timestamp = time.time()
            RECURSOS_COMPARTILHADOS[recurso_escolhido]["timestamp"] = timestamp

            # Enviamos para todos os outros processos que temos o interesse de utilizar o recurso
            for key, value in OUTROS_PROCESSOS.items():
                # Dicionario com os dados a serem enviados
                data = {
                    "recurso": recurso_escolhido,
                    "timestamp": timestamp,
                    "nomeDoProcesso": NOME_DO_PROCESSO,
                }
                # Gera um hash com os dados, após serem transformados em string
                dataHash = SHA256.new(str(data).encode('utf-8')).digest()
                # Assinar o hash
                digitalSignData = keyPair.sign(dataHash, '')
                
                # Envia a mensagem solicitando o uso do recurso
                value["objetoRemoto"] = Pyro5.api.Proxy(f"PYRONAME:{key}")
                resposta = value["objetoRemoto"].receberInscricao(digitalSignData, data)

                # Se alguem respondeu que esta utilizando o recurso, temos que esperar a notificacao 
                # de que o recurso esta livre
                if resposta == "RECURSO_OCUPADO":
                    RECURSOS_COMPARTILHADOS[recurso_escolhido]["aguardando_retorno"].append(key)

            # Se a lista estiver vazia, quer dizer que recebemos todas as respostas e 
            # que podemos utilizar o processo
            if len(RECURSOS_COMPARTILHADOS[recurso_escolhido]["aguardando_retorno"]) == 0:
                RECURSOS_COMPARTILHADOS[recurso_escolhido]["status"] = "HELD"
                    
        else:
            print(f"O {recurso_escolhido} já está sendo utilizado ou está na fila para ser utilizado.")
    else:
        print("Opção selecionada não existe!!!")

# Thread que fica esperando requisições dos outros processos
def threadFunction(daemon):
    daemon.requestLoop()                   

def findOtherProcess():
    global countLocatedProcess

    while True:
        # para cada processo no dicionario, guardaremos a sua respectiva chave publica
        countLocatedProcess = 0
        for key, value in OUTROS_PROCESSOS.items():
            # Verifica se ja temos o objeto remoto, se sim contamos ele
            if value["objetoRemoto"] != None:
                countLocatedProcess += 1
            else:
                try:
                    # Tenta pegar o objeto remoto e a chave publica do outro processo
                    value["objetoRemoto"] = Pyro5.api.Proxy(f"PYRONAME:{key}")
                    value["chavePublica"] = value["objetoRemoto"].getPubKey()
                except:
                    # Se não conseguir resetamos e tentamos de novo na proxima
                    value["objetoRemoto"] = None
                    value["chavePublica"] = None
        
        # Se ja conectamos e pegamos a chave publica de todos, podemos sair do loop
        if countLocatedProcess == len(OUTROS_PROCESSOS.items()):
            print("Objetos Remotos e Chaves Publicas salvas")
            break

        time.sleep(1)

# Thread que fica rodando o nameserver
def nameserverThread():
    Pyro5.nameserver.start_ns_loop()


# Inicia o nameserver caso ele ainda esteja rodando
def startNameServer():
    try:
        # Tenta localizar o nameserver
        ns = Pyro5.api.locate_ns()
    except:
        # Se não conseguir inicia o nameserver
        Pyro5.nameserver.start_ns(host="localhost", port=9091)
        #Inicia a thread responsavel pro esperar requisições de outros processos
        thread = threading.Thread(target=nameserverThread)
        thread.start()

def main():
    # Inicia o nameserver caso ele ainda não esteja rodando
    startNameServer()

    # Cria um Pyro daemon
    daemon = Pyro5.server.Daemon()         
    #Encontra o servidor de nomes
    ns = Pyro5.api.locate_ns()
    # Registra a classe ObjetoRemoto como um objeto Pyro
    uri = daemon.register(ObjetoRemoto)   
    # Registra o processo com um nome no servidor de nomes
    ns.register(NOME_DO_PROCESSO, uri)   

    #Inicia a thread responsavel pro esperar requisições de outros processos
    thread = threading.Thread(target=threadFunction, args=(daemon, ))
    thread.start()
    
    #Inicia a thread responsavel pro esperar requisições de outros processos
    thread = threading.Thread(target=findOtherProcess)
    thread.start()

    #Loop infinito do menu
    while True:
        menu()

if __name__ == "__main__":
    main()