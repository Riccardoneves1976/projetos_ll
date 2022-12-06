# -*- coding: utf-8 -*-

import socket
from threading import *
from urllib.parse import unquote
from google.cloud import speech_v1 as speech
from google.oauth2 import service_account
import cx_Oracle
import jellyfish as jf

listensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listensocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
port = 45231
maxcon = 10
IP = socket.gethostbyname_ex(socket.gethostname())[2][2]

listensocket.bind(('', port))

listensocket.listen(maxcon)

print("Server started at " + IP + ":" + str(port))

running = True

media = "output.mp3"

class Database():
    def __init__(self):        
        self.numFrases = 0
        self.con = cx_Oracle.connect('pythonhol/welcome@127.0.0.1/orcl')
    
    def GetFrases():
        cur = self.cursor()
        cur.execute("SELECT Tabela1.Frases FROM Tabela1")
        frases = []
        for result in cur:
            frases.append(result[0])
        return frases
    
    def SetFrase(self, frase):
        cur = self.con.cursor()
        cur.execute("insert into Tabela1.Frases values (" + str(self.numFrases) + "," + frase +")")
        self.numFrases = numFrases + 1
        
    def ResetFrases(self):
        cur = self.cursor()
        cur.execute("Delete From Tabela1")
        self.numFrases = 0
        

    def convertAudioInText(self):
        credentials = service_account.Credentials.from_service_account_file("C:/Path/To/JSON.json") #alterar as credenciais 
        scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
        
        config = speech.RecognitionConfig(
            sample_rate_hertz=48000,
        #    enable_automatic_punctuation=True,
            language_code="pt-BR",
        #    audio_channel_count=2,
            encoding=1 #LINEAR16
            )
        
        with open(media, 'rb') as f1:
            audio = speech.RecognitionAudio(content=f1.read())
            
        client = speech.SpeechClient(credentials=credentials)
        transcript = client.recognize(config=config, audio=audio).results[0].alternatives[0].transcript
        
        # encontra a frase mais parecida
        frases = self.GetFrases()
        
        minima = -1
        val = 100
        for i in range(0, len(frases)):
            c = jf.levenshtein_distance(frases[i], transcript)
            if c < val:
                minima = i
                val = c
        
        return frases[minima]


class client(Thread):
    def __init__(self, socket, address):
        Thread.__init__(self)
        self.sock = socket
        self.addr = address
        self.database = Database()
        self.start()
        
    def split(self, data):
        head = ""
        body = b"" 
        n = data.find(b"\r\n\r\n")
        if n > 0:
            head += data[0:n].decode()
            body += data[n+4:]
        else:
            body += data
        
        return (head, body)
    
    def SendMsg(self, msg_body, code):
            msg_body += "\r\n"
            response_headers = {
            'Content-Type': 'text/html; encoding=utf8',
            'Content-Length': len(msg_body),
            'Connection': 'close',
            }

            response_headers_raw = ''.join('%s: %s\r\n' % (k, v) for k, v in response_headers.items())
            response_proto = 'HTTP/1.1'
            response_status = str(code)
            response_status_text = 'OK' # this can be random

            # sending all this stuff
            r = '%s %s %s\r\n' % (response_proto, response_status, response_status_text)
            self.sock.sendall(r.encode())
            self.sock.sendall(response_headers_raw.encode())
            self.sock.sendall(b'\r\n') # to separate headers from body
            self.sock.send(msg_body.encode(encoding="utf-8"))
            
            

    def run(self):   
        message = self.sock.recv(1024*1024)
        if not message == b"":
            (head, body) = self.split(message)
            #print(head)
            
            mensagem = "Olá, você me mandou uma mensagem."
            code = 404
            
            if head.find("path=") >= 0:
                # é um arquivo de audio
                with open(media, "wb") as file:
                    file.write(body)
                    total_size = len(head)+len(body)    
                    print(f"{total_size} bytes received from POST")
                
                if self.database.numFrases == 0:
                    code = 404
                else:
                    code = 200
                    mensagem = self.database.convertAudioInText()
                    print("mensagem = " + mensagem)
            else:
                body = body.decode()
                n = body.find("Add_frase-")
                if n >= 0:
                    frase = body[n+10:]
                    frase = unquote(frase).replace("+", " ").strip()
                    print(frase)
                    mensagem = "Frase \"" + frase + "\" adicionada às opções."
                    self.database.SetFrase(frase)
                    code = 200
                    
                elif body.find("Reset_frases") >= 0:
                    #reset as frases
                    print("reset")
                    mensagem = "opções de mensagens foram resetadas."
                    code = 200
                    self.database.ResetFrases()
            
            self.SendMsg(mensagem, code)
        else:
            self.sock.close()

while running:
    (clientsocket, address) = listensocket.accept()
    print("new conn!")
    print(address)
    client(clientsocket, address)
