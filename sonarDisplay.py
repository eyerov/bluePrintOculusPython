import cv2
import numpy as np


class warpSonar:
    def __init__(self):
        self.srcX = None
        self.srcY = None

        self.mapx = None
        self.mapy = None


    def jls_extract_def(self):
        
        return 

    def createMaps(self, srcX, srcY, degVec):

        self.srcY = srcY
        self.srcX = srcX

        radVec = np.deg2rad(degVec)

        #radVec2 = np.linspace(radVec[0], radVec[-1], len(radVec)*2)
        #import ipdb; ipdb.set_trace()

        extW = srcX/2+srcY*np.sin(radVec[0])
        
        if extW < 0:
            self.mapx = np.zeros( (srcY, int(srcX+2*np.abs(extW)) ), dtype='float32')
            self.mapy = self.mapx.copy()
            shiftX = np.abs(extW)
        else:
            self.mapx = np.zeros( (srcY, int(srcX) ), dtype='float32')
            self.mapy = self.mapx.copy()
            shiftX = 0

        ang     = radVec[-1] 
        denFac  = 1

        for i,teta in enumerate(np.array(np.linspace(-ang,ang,srcX*denFac))):
        #for i,teta in enumerate(radVec):
            #for j in range(srcY):
            for j in np.linspace(0, srcY, srcY*denFac):
                b=j
                py = b*np.cos(teta)
                px = srcX/2+b*np.sin(teta)
                try:
                    self.mapx[int(py), int(px+shiftX)]=i/denFac
                    self.mapy[int(py), int(px+shiftX)]=j
                except:
                    pass


    def warpSonarImage(self, metadata, img):
        sx,sy=img.shape[1],img.shape[0]
        if (sx != self.srcX) or (sy != self.srcY):
            degVec = metadata["beamsDeg"]
            self.createMaps(sx,sy,degVec)
            print('init')

        warped = cv2.remap(img, self.mapx, self.mapy, cv2.INTER_CUBIC)
        
        return warped



if __name__=='__main__':
    import pickle
    
    cv2.namedWindow('Original Image', 0)
    cv2.namedWindow('Warped Image', 0)
    

    with open('inData.pkl', 'rb') as fid:
        metadata, sonImg = pickle.load(fid)

    cv2.imshow('Original Image', sonImg)
    ws = warpSonar()

    scales = [1.0, 1.2, 1.5, 2.0, 3.0]
    
    for scale in scales:

        inImg = cv2.resize(sonImg, None, fx=1, fy=scale)

        warped = ws.warpSonarImage(metadata, inImg)
        warped = cv2.flip(warped, 0)
        print('--->', warped.shape, inImg.shape)

        cv2.imshow('Warped Image', warped)
        cv2.waitKey(0)

    cv2.destroyAllWindows()
