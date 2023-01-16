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

def packMsg(st):
    data = []
    for key in st['attributes']:
        data.append(st['attributes'][key]['value'])

    packed = struct.pack(st['packString'], data)
    return packed


def createOculusSimpleFireMessage2(oculusId, dstDeviceId, flags = 25, rangePercent=12, gainPercent=60.0), gammaCorrection=0xff:
    st = bpStructs['structs']['OculusSimpleFireMessage2']
    attributes = st['attributes']

    attributes['oculusId']        =  oculusId
    attributes['srcDeviceId']     =  0
    attributes['dstDeviceId']     =  dstDeviceId
    attributes['msgId']           =  21
    attributes['msgVersion']      =  2
    attributes['payloadSize']     =  73
    attributes['spare2_']         =  0
    attributes['masterMode']      =  1
    attributes['pingRate']        =  1
    attributes['networkSpeed']    =  100
    attributes['gammaCorrection'] =  gammaCorrection
    attributes['flags']           =  flags
    attributes['rangePercent']    =  rangePercent
    attributes['gainPercent']     =  gainPercent
    attributes['speedOfSound']    =  0.0
    attributes['salinity']        =  0.0
    attributes['extFlags']        =  4
    attributes['reserved_0']      =  0
    attributes['reserved_1']      =  0
    attributes['reserved_2']      =  0
    attributes['reserved_3']      =  0
    attributes['reserved_4']      =  0
    attributes['reserved_5']      =  0
    attributes['reserved_6']      =  0
    attributes['reserved_7']      =  0

    ret = packMsg(st)
    return ret



def getStatusMsg(sock, T=0.01): # UDP

    statusHeaderSize = 16
    ret = None

    statusSize = bpStructs['structs']['OculusStatusMsg']['sizeof']
    stStatus   = bpStructs['structs']['OculusStatusMsg']

    recvSock = select([sock], [], [], T)[0]

    if len(recvSock) > 0:
        data = sock.recvfrom(64*1024)
        
        status = parseStruct(data[0], stStatus)
        
        status["ipAddr"]            = socket.inet_ntoa(struct.pack("I", status["ipAddr"]))
        status["ipMask"]            = socket.inet_ntoa(struct.pack("I", status["ipMask"]))
        ret = status
        
    return ret


def structParseByHeader(payload):
    headerSize = bpStructs['structs']['OculusMessageHeader']['sizeof']
    header = parseStruct(payload[:headerSize], bpStructs['structs']['OculusMessageHeader'])
    
    ret = None
    #print('cur msgId =', header['msgId'])
    if header['msgId'] in bpStructs['enums']['OculusMessageType']['revFields'].keys():
        curMsg = bpStructs['menums']['OculusMessageType']['revFields'][header['msgId']]
        if curMsg == "messageUserConfig":
            # not relevant... for parsing data (pc->sonar case...)
            payload = payload[headerSize: ]
            ret = parseStruct(payload, bpStructs['structs']["OculusUserConfig"])
            ret.update({'structName':"OculusUserConfig"})

        elif curMsg == "messageSimpleFire":
            st = bpStructs['structs']["OculusSimpleFireMessage2"]
            '''
            payload = payload[headerSize: ]
            packString = '<'
            for key in st['attributes'].keys():
                if key != "head":
                    packString += st['attributes'][key]['packStr']
                    #print(key, st['attributes'][key]['packStr'])
            '''
            ret = parseStruct(payload, st) #, packStr=packString)
            print('------> send flags:', bin(np.uint8(ret['flags'])))
            ret.update({'structName':"OculusSimpleFireMessage2"})

        elif curMsg == "messageSimplePingResult":
            st = bpStructs['structs']["OculusSimplePingResult2"]

            ret = parseStruct(payload[:st['sizeof']], st)
            
            ret.update({'structName':"OculusSimplePingResult2", 'plUsed':st['sizeof']})
            print('------> recieved flags:', bin(np.uint8(ret['flags'])))
            #import ipdb; ipdb.set_trace()
        elif curMsg == "messagePingResult":
            pass

        elif curMsg == 'messageDummy': #0xff
            pass ##print('Dummy Message')

        else:
            print( '--> ', header['msgId'] )
            print( '---> ', curMsg )
            import ipdb; ipdb.set_trace()
        
        print('<>%s<>'%curMsg, ret)

    elif header['msgId'] == 0x80:
        # user data
        data = payload[16:].decode()
        for line in data.strip().split('\n'):
            print(line)
        ret = header
    else:
        pass
        ##print('unknown msg...')
        #import ipdb; ipdb.set_trace()

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

        oculusId = -1
        dstDeviceId = -1
        # stage 1 - get sonar IP addr
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
                oculusId = status['oculusId']
                dstDeviceId = status['srcDeviceId']
                M1200dTcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                M1200dTcpSock.connect( ("%s" %status['status']['ipAddr'], tcpPort) )
                break
        
        # Handle sonar data
        if M1200dTcpSock is not None:
            initServerMsgId = 0x80

            # stage 2 - wait for sonar init message.... (0x80)

            while True:

                userConfigMsg = bpStructs['structs']['OculusUserConfig']
                userConfigMsg['attributes']['ipAddr']['value']      = 0
                userConfigMsg['attributes']['ipMask']['value']      = 0
                userConfigMsg['attributes']['dhcpEnanle']['value']  = 0

                toSend = packMsg(userConfigMsg)
                M1200dTcpSock.sendall(toSend)

                toSend = createOculusSimpleFireMessage2(oculusId, dstDeviceId)
                M1200dTcpSock.sendall(toSend)

                sonData = handleOculusMsg(M1200dTcpSock, initServerMsgId)

                if sonData is not None and sonData["msgId"] == initServerMsgId:
                    print("server connection init...")
                    break

            pingTic = time.time()
            pingCnt = 0.0

            # stage 3 - handle real time data
            while True:
                messageSimplePingResult = 0x23
                M1200dTcpSock.sendall(simpleFireMsg2)
                sonData = handleOculusMsg(M1200dTcpSock, 0x23)
                pingCnt += 1
                #import ipdb; ipdb.set_trace()
                if time.time() - pingTic >= 3:
                    pps = pingCnt/(time.time()-pingTic)
                    print("ping rate: %0.2fHz, %d"%(pps, sonData["nBeams"]) )
                    pingTic = time.time()
                    pingCnt = 0.0

