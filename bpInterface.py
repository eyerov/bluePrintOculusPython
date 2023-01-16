import numpy as np
import os
import zmq
from select import select
import socket
import time
import struct
import pickle


if not os.path.exists("oculus_h.pkl"):
    import bpStructs as bpcs
    bpcs.saveStructs2Pkl()
    bpStructs = bpcs.getBpStruct()
else:
    with open("oculus_h.pkl", 'rb') as fid:
        bpStructs = pickle.load(fid)


def parseStruct(payload, st, packStr = None):
    if packStr is None:
        packStr = st['packString']

    tmp = struct.unpack(packStr, payload)
    data = {}

    for idx, key in enumerate(st["attributes"].keys()):
        data[key] = tmp[idx]
    
    return data


def getStatusMsg(sock, T=0.01):

    statusHeaderSize = 16
    recvSock = select([sock], [], [], T)[0]
    ret = None

    statusSize = bpStructs['structs']['OculusStatusMsg']['sizeof']
    stStatus   = bpStructs['structs']['OculusStatusMsg']

    if len(recvSock) > 0:
        ret = {}
        data = sock.recvfrom(64*1024)
        
        status = parseStruct(data[0], stStatus)
        
        status["ipAddr"]            = socket.inet_ntoa(struct.pack("I", tmp[0]))
        status["ipMask"]            = socket.inet_ntoa(struct.pack("I", tmp[1]))
        payloadSize = pos+(3*4+6+9*8)-statusHeaderSize
        if hdr["payloadSize"] != payloadSize:
            print('missing status data....')
        
        ret['verInfo']= verInfo
        ret['status'] = status
        
    return ret




if __name__ == "__main__":
    

    try:    
        statusPort  = 52102 # UDP port fot init proc.
        tcpPort     = 52100 # TCP port for realtime 

        udpStatusSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpStatusSock.bind(("", statusPort))

        context = zmq.Context()
        M1200dTcpSock = None

        # get sonar status, as sonar init procedure...
        statusTic = time.time()
        statusCnt = 0.0
        while True:
            
            status = getStatusMsg(udpStatusSock)
            if status is not None:
                statusCnt += 1
            if time.time() - statusTic >= 3:
                sps = statusCnt/(time.time()-statusTic)
                print("Status rate: %0.2fHz"%sps)
                statusTic = time.time()
                statusCnt = 0.0
            
            if (status is not None) and ('ipAddr' in status['status'].keys()):
                print("Initiate Tcp connection to: %s "%status['status']['ipAddr'])
                M1200dTcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                M1200dTcpSock.connect( ("%s" %status['status']['ipAddr'], tcpPort) )
                break
