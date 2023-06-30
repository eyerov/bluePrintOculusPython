import numpy as np
import os
import zmq
import socket
import time
import bpHandler
import cv2
import sonarDisplay 
import sys
import pickle
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
        press 'a' to change aperture

        TBD..."""

    print(usege)
    if len(sys.argv)>1:
        live = (sys.argv[1]=="live")
    else:
        print("python bpSample.py live\nOR\npython bpSample.py notlive")

   
    winName = 'sonData'
    cv2.namedWindow(winName, 0)
    ws = sonarDisplay.warpSonar()
    warpIm = True

    try:    
        if live:
            statusPort  = 52102
            tcpPort     = 52100

            udpStatusSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udpStatusSock.bind(("", statusPort))

        context = zmq.Context()
        M1200dTcpSock = None

        # get sonar status (and ip), as sonar init procedure...
        statusTic = time.time()
        statusCnt = 0.0
        i=0
        while True:
            
            if live:
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
            else:break

        
        # Handle sonar data
        if (M1200dTcpSock is not None) or (not live):
            
            # init sonar values
            nBins           = 256
            pingRate        = 15    #[Hz] 
            gammaCorrection = 0xff  # 0xff -> 1 byte (0-255)
            rng             = 12    # [m] # in wide aperature up to 40[m], in narrow, up to 10[m]
            gainVal         = 60    # [%]
            sOs             = 0     # [m/s], speed of sound, 0->precalculated
            salinity        = 0     # ? (ppt}
            is16Bit         = False
            aperture        = 1     # 1-> wide, 2->low


            if live:
                simpleFireMsg2 = bpHandler.createOculusFireMsg(status['hdr'], 
                                                        nBins, 
                                                        pingRate,
                                                        gammaCorrection, 
                                                        rng,
                                                        gainVal,
                                                        sOs,
                                                        salinity,
                                                        is16Bit,
                                                        aperture)

            pingTic = time.time()
            pingCnt = 0.0

            #userConfig = bpHandler.setUserConfigMsg(pingRate=0x01)
            #M1200dTcpSock.send(userConfig)

            doCahngeStatus = False
            nBeams = -1
            nRanges = -1

            dt = 0.5
            tic = time.time()-dt
            
            while True:
                time.sleep(0.001)
                if time.time() - tic >= dt:
                    if live:
                        M1200dTcpSock.sendall(simpleFireMsg2)
                    tic = time.time()
                if live:
                    sonData = bpHandler.handleOculusMsg(M1200dTcpSock)
                else:
                    if not os.path.exists(f"sonar/data{i}.pickle"):
                        print(f"sonar/data{i}.pickle Doesn't exist. Resetting i to 0")
                        i=0
                    with open(f"sonar/data{i}.pickle", "rb") as input_file:
                        sonData = pickle.load(input_file)
                print(i)
                i=i+1
                if sonData is not None and (sonData[0]['msgId']==0x23 or sonData[0]['msgId']==0x22):
                    pingCnt += 1
                    nBeams = sonData[0]["nBeams"]
                    nRanges = sonData[0]["nRanges"]

                    showIm = sonData[1]
                    if warpIm:
                        showIm = ws.warpSonarImage(sonData[0], sonData[1])
                    
                    cv2.imshow(winName, showIm)
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
                        rng += 0.5 #[m]
                        rng = min(40, rng)
                        print('set range to %f [m]'%rng)
                        doCahngeStatus = True
                    elif key == ord('f'):
                        rng -= 0.5 #[m]
                        rng = max(1, rng)
                        print('set range to %f [m]'%rng)
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
                    elif key==ord('a'):
                        if aperture==1:
                            aperture=2
                            print("toggle aperture to: narrow")
                        else:
                            aperture=1
                            print("toggle aperture to: wide")
                        doCahngeStatus = True
                    elif key==ord('q') or key == 27:
                        print('exit')
                        break 

                    if not live:
                        doCahngeStatus=False
                    if doCahngeStatus:
                        doCahngeStatus = False 
                        simpleFireMsg2 = bpHandler.createOculusFireMsg(status['hdr'], 
                                                            nBins, 
                                                            pingRate,
                                                            gammaCorrection, 
                                                            rng,
                                                            gainVal,
                                                            sOs,
                                                            salinity,
                                                            is16Bit,
                                                            aperture)
                        M1200dTcpSock.sendall(simpleFireMsg2)

                    
                if time.time() - pingTic >= 3:
                    pps = pingCnt/(time.time()-pingTic)
                    print("ping rate: %0.2fHz, %d %d"%(pps, nBeams, nRanges) )
                    pingTic = time.time()
                    pingCnt = 0.0
                
                    
    except:           
        import traceback
        traceback.print_exc()
    finally:
        if live:
            print("terminate connection to sonar:tcp://%s:%s" %(status['status']['ipAddr'], tcpPort) )
            M1200dTcpSock.close() #"tcp://%s:%s" %(status['status']['ipAddr'], tcpPort) )
        
            
        
            





