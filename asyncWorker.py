from geo_question_parser import QuestionParser, TypesToQueryConverter

import zmq
import threading
import json

import traceback
import sys

import socket

import signal

# [SC][TODO]
import time


# [SC] to capture the keyboard interrput command (Ctrl + C)
signal.signal(signal.SIGINT, signal.SIG_DFL)

# [SC][TODO] these should be set from a command line
workerInstanceCount = 5
frontendPort = "5570"

defWorkerInstanceCount = 10
defIp = "127.0.0.1"
defFrontendPort = "5570"
frontendBind = ""
backendBind = "inproc://backend"


class Logger:
    # [SC] static variables
    printConsole = True

    ERROR_TYPE = "ERROR"
    WARNING_TYPE = "WARNING"
    INFO_TYPE = "INFO"

    # [SC] Custom static printing method.
    # @param    string  type    Message type (ERROR, WARNING, INFO, etc).
    # @param    string  method  Name of the method that call this method.
    # @param    string  msg     Message to be printed.
    # @return   string          The composed log text as string
    @staticmethod
    def cPrint(type, method, msg):
        msg = f"{type}: {msg} in method '{method}'"
        
        if Logger.printConsole: 
            print(msg)
        
        return msg


# [SC] this class implement a worker
class QparserWorker(threading.Thread):
    def __init__(self, context, wId):
        threading.Thread.__init__ (self)
        self.context = context
        self.wId = wId
    
    def run(self):
        methodName = "QparserWorker.run"
        
        global backendBind
    
        # [SC] connect worker to a inter-process socket from a shared context
        # [SC] zmq.DEALER si required instead of zmq.REP
        worker = self.context.socket(zmq.DEALER)
        worker.connect(backendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Started worker '{self.wId}' on a inter-process socket '{backendBind}'")
        
        while True:
            cId = ""
            qStr = ""
            
            try:
                # [SC] receive client id at first
                cId = worker.recv_string()
                # [SC] receive the question string
                qStr = worker.recv_string()
                Logger.cPrint(Logger.INFO_TYPE, methodName
                    , f"Worker '{self.wId}' received a request. Client: '{cId}'; Message: '{qStr}'") 
            except Exception as e:
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                    , f"============================ Exception in worker '{self.wId}' while receiving a request from the broker")
                exc_info = sys.exc_info()
                Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
                # [SC][TODO] more graceful handling of errors is needed here
                continue
            
            msg = ""
            qParsed = {}
            
            try:
                # [SC][TODO] do work here
                # [SC][TODO] serialize the final output into a string and assign to the variable 'msg'
                parser = QuestionParser(None)
                qParsed = parser.parseQuestion(qStr)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"Parsed the question '{qStr}'")
                
                cctAnnotator = TypesToQueryConverter()
                cctAnnotator.algebraToQuery(qParsed, True, True)
                cctAnnotator.algebraToExpandedQuery(qParsed, False, False)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"Annotated the question '{qStr}'")

                # [SC] serialize the final parse tree
                msg = json.dumps(qParsed)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"The final parse tree result: \n{msg}")
            
                # [SC][TODO] for testing only
                #qParsed = {"qstr": qStr}

                # [SC][TODO] for testing only
                #time.sleep(int(qStr))
                #time.sleep(20)
                
                # [SC][TODO] for testing only
                #msg = json.dumps(qParsed)
            except Exception as e:
                eMsg = Logger.cPrint(Logger.ERROR_TYPE, methodName
                    , "============================ Exception while parsing/annotating the question")
                exc_info = sys.exc_info()
                eMsg = eMsg + "\n" + Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
                qParsed["error"] = eMsg
                msg = json.dumps(qParsed)
            finally:
                worker.send_string(cId, zmq.SNDMORE)
                worker.send_string(msg)
        
        worker.close()


# [SC] this class implement a broker mediating between workers and clients
class QparserBroker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__ (self)
        
    def run(self):
        methodName = "QparserBroker.run"
    
        global frontendBind
        global backendBind
        global workerInstanceCount
        
        # [SC] this zmq context is shared between worker and broker
        context = zmq.Context()
        
        # [SC] client connects to this socket
        frontend = context.socket(zmq.ROUTER)
        frontend.bind(frontendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Bound broker frontend to '{frontendBind}'")
        
        # [SC] worker connects to this inter-process socket
        backend = context.socket(zmq.DEALER)
        backend.bind(backendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Bound broker backend to an inter-process port '{backendBind}'")
        
        # [SC] creating worker instances
        workers = []
        for i in range(workerInstanceCount):
            worker = QparserWorker(context, i)
            worker.start()
            workers.append(worker)
        
        # [SC] creating a poller to forward clint and worker messages
        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)
        Logger.cPrint(Logger.INFO_TYPE, methodName, "Started the poller in the broker")
        
        while True:
            # [SC][TODO] more error handling is needed
            # [SC][TODO] if two clients use the same id then the one who connects last is ignored; need to fix it
            try:
                sockets = dict(poller.poll())
                
                # [SC] received a request from a client, forwarding the request to a worker
                if sockets.get(frontend) == zmq.POLLIN:
                    # [SC] receive client id at first
                    cId = frontend.recv_string()
                    # [SC] receive the question string
                    qStr = frontend.recv_string()
                    
                    Logger.cPrint(Logger.INFO_TYPE, methodName
                        , f"Forwarding a request from a client to a worker. Client: '{cId}'; Message: '{qStr}'")
                    backend.send_string(cId, zmq.SNDMORE)
                    backend.send_string(qStr)
                
                # [SC] received a reply from the worker, forwarding the reply to the client
                if sockets.get(backend) == zmq.POLLIN:
                    # [SC] receive client id at first
                    cId = backend.recv_string()
                    # [SC] receive the reply message (parse tree)
                    msg = backend.recv_string()
                    
                    Logger.cPrint(Logger.INFO_TYPE, methodName
                        , f"Forwarding a reply from the worker to the client. Client: '{cId}'; Message: '{msg}'")
                    frontend.send_string(cId, zmq.SNDMORE)
                    frontend.send_string(msg)
            except Exception as e:
                Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Exception in the broker")
                exc_info = sys.exc_info()
                Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info))) 
                    
        frontend.close()
        backend.close()
        context.term()



def isPortBindable(ip, port):
    methodName = "isOpenPort"
    
    testSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        testSocket.bind((ip, int(port)))
        return True
    except Exception as e:
        Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Problem with the port {port} at {ip}")
        exc_info = sys.exc_info()
        Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
        return False
    finally:
        testSocket.close()


def main():
    methodName = "main"
    
    global frontendPort
    global defFrontendPort
    global frontendBind
    global defIp
    
    global workerInstanceCount
    global defWorkerInstanceCount
    
    # [SC] make sure the port is usable
    if not isPortBindable(defIp, frontendPort):
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Cannot open port '{frontendPort}'")
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Attempting the default port '{defFrontendPort}'")
        
        if isPortBindable(defIp, defFrontendPort):
            frontendPort = defFrontendPort
        else:
            Logger.cPrint(Logger.ERROR_TYPE, methodName, f"Cannot open the default port '{defFrontendPort}'")
            Logger.cPrint(Logger.ERROR_TYPE, methodName, f"Unable to start the server. No available ports")
            return
    
    # [SC] make sure a valid number for instance is provided
    try:
        workerInstanceCount = int(workerInstanceCount)
        if workerInstanceCount <= 0:
            raise Exception(f"Invalid worker instance count '{workerInstanceCount}'. Worker instance count should be 1 or higher integer number.")
    except Exception as e:
        Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Invalid worker instance count")
        exc_info = sys.exc_info()
        Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
        
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Using the default worker instance count '{defWorkerInstanceCount}'")
        workerInstanceCount = defWorkerInstanceCount
    
    # [SC] compose bind address for a frontend client
    frontendBind = f"tcp://{defIp}:{frontendPort}"

    # [SC] start the broker server
    server = QparserBroker()
    server.start()
    server.join()


if __name__ == "__main__":
    main()