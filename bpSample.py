import numpy as np
import os
import zmq
import socket
import time
import bpHandler
import cv2


if __name__ == "__main__":
    usege = """usage:\n  
    while sonar image is on scope you can do the following actions:
        press 'h' to get 512 beams
        press 'n' to get 256 beams
        press 'r' to increase sonar range by 0.5 [m]
        press 'f' to decrease sonar range by -0.5 [m]
        press 'g' to increase gain percentage by 1[%]
        press 'b' to increase gain percentage by 1[%]
        press 'z' to sample 16bit image (it provide 8bit streched image, but at the handler you will have the 16bit)

        TBD..."""

    print(usege)

   
    winName = 'sonData'
    cv2.namedWindow(winName, 0)

    try:    
        statusPort  = 52102
        tcpPort     = 52100

        udpStatusSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpStatusSock.bind(("", statusPort))

        context = zmq.Context()
        M1200dTcpSock = None

        # get sonar status (and ip), as sonar init procedure...
        statusTic = time.time()
        statusCnt = 0.0
        while True:
            
            status = bpHandler.getStatusMsg(udpStatusSock)
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

        
        # Handle sonar data
        if M1200dTcpSock is not None:
            
            # init sonar values
            nBins           = 256
            pingRate        = 10    #[Hz] 
            gammaCorrection = 0xff  # 0xff -> 1
            range           = 12    # [m]
            gainVal         = 60    # [%]
            sOs             = 0     # [m/s], speed of sound, 0->precalculated
            salinity        = 0     # ? (pps}
            is16Bit         = False


            simpleFireMsg2 = bpHandler.createOculusFireMsg(status['hdr'], 
                                                    nBins, 
                                                    pingRate,
                                                    gammaCorrection, 
                                                    range,
                                                    gainVal,
                                                    sOs,
                                                    salinity,
                                                    is16Bit)

            pingTic = time.time()
            pingCnt = 0.0

            #userConfig = bpHandler.setUserConfigMsg(pingRate=0x01)
            #M1200dTcpSock.send(userConfig)

            doCahngeStatus = False
            nBeams = -1
            nRanges = -1

            
            while True:
                time.sleep(0.001)
                M1200dTcpSock.sendall(simpleFireMsg2)
                sonData = bpHandler.handleOculusMsg(M1200dTcpSock)
                
                if sonData is not None and sonData[0]['msgId']==0x23:
                    pingCnt += 1
                    nBeams = sonData[0]["nBeams"]
                    nRanges = sonData[0]["nRanges"]
                    
                    cv2.imshow(winName, sonData[1])
                    key = cv2.waitKey(1)&0xff
                    if key==ord('h'):
                        print('set 512 bins')
                        nBins = 512
                        doCahngeStatus = True
                    elif key==ord('n'):
                        print('set 256 bins')
                        nBins = 256
                        doCahngeStatus = True
                    elif key == ord('r'):
                        range += 0.5 #[m]
                        range = min(40, range)
                        print('set range to %f [m]'%range)
                        doCahngeStatus = True
                    elif key == ord('f'):
                        range -= 0.5 #[m]
                        range = max(1, range)
                        print('set range to %f [m]'%range)
                        doCahngeStatus = True
                    elif key == ord('g'):
                        gainVal += 1 #[m]
                        gainVal = min(100, gainVal)
                        print('set gain to %f [%%]'%gainVal)
                        doCahngeStatus = True
                    elif key == ord('b'):
                        gainVal -= 1 
                        gainVal = max(1, gainVal)
                        print('set gain to %f [%%]'%gainVal)
                        doCahngeStatus = True
                    elif key==ord('z'):
                        is16Bit = not is16Bit
                        doCahngeStatus = True
                        print("toggle 16bit to:", is16Bit)
                    elif key==ord('q') or key == 27:
                        print('exit')
                        break 

                    
                    if doCahngeStatus:
                        doCahngeStatus = False 
                        simpleFireMsg2 = bpHandler.createOculusFireMsg(status['hdr'], 
                                                            nBins, 
                                                            pingRate,
                                                            gammaCorrection, 
                                                            range,
                                                            gainVal,
                                                            sOs,
                                                            salinity,
                                                            is16Bit)

                    
                if time.time() - pingTic >= 3:
                    pps = pingCnt/(time.time()-pingTic)
                    print("ping rate: %0.2fHz, %d %d"%(pps, nBeams, nRanges) )
                    pingTic = time.time()
                    pingCnt = 0.0
                
                    
    except:           
        import traceback
        traceback.print_exc()
    finally:
        print("terminate connection to sonar:tcp://%s:%s" %(status['status']['ipAddr'], tcpPort) )
        M1200dTcpSock.close() #"tcp://%s:%s" %(status['status']['ipAddr'], tcpPort) )
        
            
        
            





