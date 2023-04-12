import struct
import os
from select import select
import socket
import numpy as np
import time
import cv2

import pickle

if not os.path.exists("oculus_h.pkl"):
    import bpStructs as bpcs
    bpcs.saveStructs2Pkl()
    bpStructs = bpcs.getBpStruct()
else:
    with open("oculus_h.pkl", 'rb') as fid:
        bpStructs = pickle.load(fid)


def parseBpStruct(payload, st, packStr = None):
    if packStr is None:
        packStr = st['packString']
    
    tmp = struct.unpack(packStr, payload)
    data = {}

    for idx, key in enumerate(st["attributes"].keys()):
        data[key] = tmp[idx]
    
    return data



def recvall(sock):
    #BUFF_SIZE = 4096 # 4 KiB
    BUFF_SIZE = 8192 # 8 KiB
    data = b''
    while True:
        time.sleep(0.001)
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    
    return data



def getStatusMsg(sock, T=0.01):
    '''
    Status message should recieved in 1Hz and its structure is:
    struct OculusStatusMsg
    {
    public:
    OculusMessageHeader hdr;

    uint32_t   deviceId;
    OculusDeviceType   deviceType;
    OculusPartNumberType partNumber;
    uint32_t   status;
    OculusVersionInfo versinInfo;
    uint32_t   ipAddr;
    uint32_t   ipMask;
    uint32_t   connectedIpAddr;
    uint8_t  macAddr0;
    uint8_t  macAddr1;
    uint8_t  macAddr2;
    uint8_t  macAddr3;
    uint8_t  macAddr4;
    uint8_t  macAddr5;
    double temperature0;
    double temperature1;
    double temperature2;
    double temperature3;
    double temperature4;
    double temperature5;
    double temperature6;
    double temperature7;
    double pressure;
    };
    '''

    statusHeaderSize = 16
    recvSock = select([sock], [], [], T)[0]
    ret = None
    if len(recvSock) > 0:
        ret = {}
        data = sock.recvfrom(64*1024)
        tmp = struct.unpack("<HHHHHIH",data[0][:statusHeaderSize])
        hdr = { "oculusId":     tmp[0],
                "srcDeviceId":  tmp[1],
                "dstDeviceId":  tmp[2],
                "msgId":        tmp[3],
                "msgVersion":   tmp[4],
                "payloadSize":  tmp[5],
                "spare2":       tmp[6]
                }
        
        ret['hdr'] = hdr
        status = {}
        pos = statusHeaderSize
        tmp = struct.unpack("<IHHI",data[0][pos:pos+12])
        status["deviceId"]   = tmp[0]       
        status["deviceType"] = tmp[1]
        status["partNumber"] = tmp[2]
        status["status"]     = tmp[3]
        pos = pos+12
        tmp = struct.unpack("<IIIIII",data[0][pos:pos+6*4])
        verInfo = {}
        verInfo["firmwareVersion0"] = tmp[0] # The arm0 firmware version major(8 bits), minor(8 bits), build (16 bits) 
        verInfo["firmwareDate0"]    = tmp[1] # The arm0 firmware date
        verInfo["firmwareVersion1"] = tmp[2] # The arm1 firmware version major(8 bits), minor(8 bits), build (16 bits)
        verInfo["firmwareDate1"]    = tmp[3] # The arm1 firmware date
        verInfo["firmwareVersion2"] = tmp[4] # The bitfile version
        verInfo["firmwareDate2"]    = tmp[5] # The bitfile date
        pos = pos+6*4
        tmp = struct.unpack("<"+"I"*3+"B"*6+"d"*9,data[0][pos:pos+(3*4+6+9*8)])
        status["ipAddr"]            = socket.inet_ntoa(struct.pack("I", tmp[0]))
        status["ipMask"]            = socket.inet_ntoa(struct.pack("I", tmp[1]))
        payloadSize = pos+(3*4+6+9*8)-statusHeaderSize
        if hdr["payloadSize"] != payloadSize:
            print('missing status data....')
        
        ret['verInfo']= verInfo
        ret['status'] = status
        
    return ret



def createOculusFireMsg(hdr, nBins = 256, pingRate=10, gammaCorrection=0xff, rng=12.0, gainVal=60.0, sOs=0, salinity=0, is16bit=False, aperture=1):
    '''
    typedef struct 
    {
    public:
        OculusMessageHeader head;     // The standard message header

        uint8_t masterMode;           // mode 0 is flexi mode, needs full fire message (not available for third party developers)
                                        // mode 1 - Low Frequency Mode (wide aperture, navigation)
                                        // mode 2 - High Frequency Mode (narrow aperture, target identification)
        PingRateType pingRate;        // Sets the maximum ping rate.
        uint8_t networkSpeed;         // Used to reduce the network comms speed (useful for high latency shared links)
        uint8_t gammaCorrection;      // 0 and 0xff = gamma correction = 1.0
                                        // Set to 127 for gamma correction = 0.5
        uint8_t flags;                // bit 0: 0 = interpret range as percent, 1 = interpret range as meters
                                        // bit 1: 0 = 8 bit data, 1 = 16 bit data
                                        // bit 2: 0 = wont send gain, 1 = send gain
                                        // bit 3: 0 = send full return message, 1 = send simple return message
        double range;                 // The range demand in percent or m depending on flags
        double gainPercent;           // The gain demand
        double speedOfSound;          // ms-1, if set to zero then internal calc will apply using salinity
        double salinity;              // ppt, set to zero if we are in fresh water
    } OculusSimpleFireMessage;
    '''

    '''
    mode 0 is flexi mode, needs full fire message (not available for third party developers)
    mode 1 - Low Frequency Mode (wide aperture, navigation)
    mode 2 - High Frequency Mode (narrow aperture, target identification)
    type: uint8_t
    '''
    if int(apetrure) != 1 and int(aperture) != 2:
        aperture = 1
        print('bad aperture value, 1->wide, 2->narrow')
    masterMode = int(aperture) # type uint8_t
    '''
    enum PingRateType : uint8_t
    {
    pingRateNormal  = 0x00, // 10Hz max ping rate
    pingRateHigh    = 0x01, // 15Hz max ping rate
    pingRateHighest = 0x02, // 40Hz max ping rate
    pingRateLow     = 0x03, // 5Hz max ping rate
    pingRateLowest  = 0x04, // 2Hz max ping rate
    pingRateStandby = 0x05, // Disable ping
    };
    type: uint8_t
    '''
    pingRateDict = {0:0x05, 
                10:0x00, 
                15:0x01,
                40:0x02,
                5:0x03,
                2:0x04 }
    if pingRate not in pingRateDict:
        print("wrong ping rate...")
        pingRate        = pingRateDict[10]  #type: uint8_t
    else:
        pingRate        = pingRateDict[pingRate]  #type: uint8_t

    
    networkSpeed    = 0xff  # type uint8_t; The max network speed in Mbs , set to 0x00 or 0xff to use link speed
    gammaCorrection = gammaCorrection  # type uint8_t; 0 and 0xff = gamma correction = 1.0

    if nBins == 512:
        fff = 0b1001101
    else:
        fff = 0b0001101

    if is16bit:
        fff = 0b0001101 | 0b0000010

    flags           = fff # uint8_t;  
                          # bit 0: 0 = interpret range as percent, 1 = interpret range as meters
                          # bit 1: 0 = 8 bit data, 1 = 16 bit data
                          # bit 2: 0 = wont send gain, 1 = send gain
                          # bit 3: 0 = send full return message, 1 = send simple return message
    
    if aperture == 1:
        maxRange = 40 # [m]
    elif aperture == 2:
        maxRange = 10 # [m]

    rng = min(max(rng,1), maxRange)
    rangePercent    = rng       # type double
    gainPercent     = gainVal   # type double
    speedOfSound    = sOs       # type double; 0->internal calculation
    salinity        = salinity  # type double; 0-> fresh water(?)
    
    '''
    enum OculusMessageType : uint16_t
    {
    messageSimpleFire         = 0x15,
    messagePingResult         = 0x22,
    messageSimplePingResult   = 0x23,
    messageUserConfig		  = 0x55,
    messageDummy              = 0xff,
    };

    '''
    messageSimpleFireType = 0x15

    payloadSize = 5*1 + 4*8
    ret = struct.pack("<HHHHHIH", hdr["oculusId"],
                                  hdr["srcDeviceId"],
                                  hdr["dstDeviceId"],
                                  messageSimpleFireType,
                                  hdr["msgVersion"],
                                  payloadSize,
                                  hdr["spare2"])
    
    ret += struct.pack('<' + 'B'*5 + 'd'*4, masterMode, 
                                       pingRate, 
                                       networkSpeed,
                                       gammaCorrection, 
                                       flags,
                                       rangePercent,
                                       gainPercent,
                                       speedOfSound,
                                       salinity,
                            )
    return ret



def setUserConfigMsg(pingRate=0x01, gammaCorrection=0xff, range=12.0, gainVal=60.0, sOs=0, salinity=0 ):
    #not in use

    st = bpStructs['structs']['OculusSimpleFireMessage2']
    st['attributes']['oculusId'       ]['value'] = 20307
    st['attributes']['srcDeviceId'    ]['value'] = 0
    st['attributes']['dstDeviceId'    ]['value'] = 17936
    st['attributes']['msgId'          ]['value'] = 21
    st['attributes']['msgVersion'     ]['value'] = 2
    st['attributes']['payloadSize'    ]['value'] = 73
    st['attributes']['spare2_'        ]['value'] = 0
    st['attributes']['masterMode'     ]['value'] = 1
    st['attributes']['pingRate'       ]['value'] = pingRate
    st['attributes']['networkSpeed'   ]['value'] = 0x00
    st['attributes']['gammaCorrection']['value'] = gammaCorrection
    st['attributes']['flags'          ]['value'] = 25
    st['attributes']['rangePercent'   ]['value'] = range    #[m]
    st['attributes']['gainPercent'    ]['value'] = gainVal  #[%]
    st['attributes']['speedOfSound'   ]['value'] = sOs      #[m/s]
    st['attributes']['salinity'       ]['value'] = salinity
    st['attributes']['extFlags'       ]['value'] = 4
    st['attributes']['reserved_0'     ]['value'] = 0
    st['attributes']['reserved_1'     ]['value'] = 0
    st['attributes']['reserved_2'     ]['value'] = 0
    st['attributes']['reserved_3'     ]['value'] = 0
    st['attributes']['reserved_4'     ]['value'] = 0
    st['attributes']['reserved_5'     ]['value'] = 0
    st['attributes']['reserved_6'     ]['value'] = 0
    st['attributes']['reserved_7'     ]['value'] = 0

    msg = b''
    ini = st['packString'][0]
    for i, key in enumerate(st['attributes']):
         msg += struct.pack(ini+st['packString'][i+1] ,st['attributes'][key]['value'])
    
    return msg

def structParseByHeader(payload):
    headerSize = bpStructs['structs']['OculusMessageHeader']['sizeof']
    header = parseBpStruct(payload[:headerSize], bpStructs['structs']['OculusMessageHeader'])
    
    #print('--->>', len(payload))
    ret = None
    #print('cur msgId =', header['msgId'])
    if header['msgId'] in bpStructs['enums']['OculusMessageType']['revFields'].keys():
        curMsg = bpStructs['enums']['OculusMessageType']['revFields'][header['msgId']]
        if curMsg == "messageUserConfig":
            # not relevant... for parsing data (pc->sonar case...)
            payload = payload[headerSize: ]
            ret = parseBpStruct(payload, bpStructs['structs']["OculusUserConfig"])
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
            ret = parseBpStruct(payload, st) #, packStr=packString)
            #print('------> send flags:', bin(np.uint8(ret['flags'])))
            ret.update({'structName':"OculusSimpleFireMessage2"})
            print('---1---') 
            #import ipdb; ipdb.set_trace()
            

        elif curMsg == "messageSimplePingResult":
            st = bpStructs['structs']["OculusSimplePingResult"]
            ret = parseBpStruct(payload[:st['sizeof']], st)
            ret.update({'structName':"OculusSimplePingResult", 'plUsed':st['sizeof']})

            #print('------> recieved flags:', bin(np.uint8(ret['flags'])))
            #print('---2---') 
            #import ipdb; ipdb.set_trace()
        elif curMsg == "messagePingResult":
            pass

        elif curMsg == 'messageDummy': #0xff
            pass ##print('Dummy Message')

        else:
            print( '--> ', header['msgId'] )
            print( '---> ', curMsg )
            import ipdb; ipdb.set_trace()
        
        #print('<>%s<>'%curMsg, ret)

    elif header['msgId'] == 0x80:
        # user data
        try:
            data = payload[16:].decode()
            for line in data.strip().split('\n'):
                print(line)
            header['structName'] = 'serverInit'
        except:
            pass
        ret = header
    else:
        pass
        ##print('unknown msg...')
        #import ipdb; ipdb.set_trace()

    return ret


class bpSonarData():
    def __init__(self):
        dataStarted = False

        self.imData = b''
        self.sumData = 0

        self.w              = -1
        self.h              = -1
        self.offset         = -1
        self.mSize          = -1
        self.metaDataSize   = -1

        self.beamsDeg       = None
        self.imData         = None
        self.sumData        = -1
        self.imSize         = -1
        self.metaData       = None
        self.is16Bit        = False

        self.imReady        = False
        

    def initSonarData(self, metaData, data):

        self.imData         = b''
        self.sumData        = 0
    
        self.metaData       = metaData
        self.imReady        = False
        
        #print('start of im...')
        self.w              = metaData['nBeams']
        self.h              = metaData['nRanges']
        self.offset         = metaData['imageOffset']
        self.mSize          = metaData['messageSize']
        self.metaDataSize   = metaData['plUsed']
        
        if (metaData['flags'] & 0b0010)== 0b10:
            #print('16Bit!')
            self.is16Bit = True
        else:
            self.is16Bit = False
        

        pl = data##[data['plUsed']:]
        self.beamsDeg = np.frombuffer(pl[self.metaDataSize:self.metaDataSize+self.w*2], dtype=np.short)/100.0
        
        self.metaData['beamsDeg'] = self.beamsDeg
        self.imData = pl

        self.sumData += len(self.imData)
        self.imSize = metaData['imageSize']

        if self.sumData >= self.imSize:
            try:
                self.extractImage()
            except:
                import traceback
                traceback.print_exc()

    def extractImage(self):
        if self.is16Bit:
                if self.w == 256:
                    #self.offset = self.w*4-2
                    dW = 2
                elif self.w == 512:
                    #not possible....
                    self.offset = self.w*2-2
                    dW = 2
                tmp = np.frombuffer(self.imData[self.offset:self.offset+(self.w+dW)*self.h*2], dtype='uint16').reshape((self.h, self.w+dW))
                tmp = tmp[:,dW:-1]
                tmp = tmp-np.min(tmp)
                self.sonarImg = ( tmp/np.max(tmp) * 255 ).astype('uint8')
        else:
            if self.w == 256:
                dW = 4
                #self.offset = self.w*6-1 #1524 +11
            elif self.w == 512:
                #pass
                dW = 4
                #self.offset = self.w*3-1
            
            tmp = np.frombuffer(self.imData[self.offset:self.offset+(self.w+dW)*self.h], dtype='uint8').reshape((self.h, self.w+dW))
            self.sonarImg = tmp[:,dW:].astype('uint8')
        #print('--->', self.sonarImg.shape, self.w, self.h, self.offset, self.is16Bit)
            
        self.imReady        = True
        
    def addSonarData(self, payload):

        self.imData += payload
        self.sumData = len(self.imData)
        ##print('sum Data =', sumData)
        if self.sumData >= self.imSize:
            try:
                self.extractImage()
            except:
                import traceback
                traceback.print_exc()
            #import ipdb; ipdb.set_trace()
    
    def isImageReady(self):
        return self.imReady

    def getSonarData(self):
        if self.imReady:
            return self.metaData, self.sonarImg
        return None
            

bpSonarData = bpSonarData()

def handleOculusMsg(sock):
    
    recvSock = select([sock], [], [], 0.05)[0]
    ret = None
    if len(recvSock) > 0:
        
        payload = recvall(sock) 
        metaData = structParseByHeader(payload)
        
        if metaData is not None:
            if metaData["msgId"] == 0x23: #metaData['structName'] == "OculusSimplePingResult":

                
                bpSonarData.initSonarData(metaData, payload)
                
                while not bpSonarData.isImageReady():
                    recvSock = select([sock], [], [], 0.05)[0]
                    if len(recvSock) > 0:
                        payload = recvall(sock) 
                        bpSonarData.addSonarData(payload)
                    
                ret = bpSonarData.getSonarData()

            elif metaData["msgId"] == 0x80: #user data, text...
                ret = [metaData]
                
                
            elif metaData["msgId"] == 0xff:
                print('dummy msg...')
            
            else:
                print('mmmm msg...', metaData["msgId"])
            
    return ret
