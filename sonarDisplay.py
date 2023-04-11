import cv2
import numpy as np


class warpSonar:
    def __init__(self):
        self.srcX = None
        self.srcY = None

        self.mapx = None
        self.mapy = None


    def createMaps(self, srcX, srcY, degVec):

        #mapx=np.zeros(img.shape,dtype='float32')
        self.srcY = srcY
        self.srcX = srcX

        self.mapx=np.zeros( (srcY, int(srcX) ), dtype='float32')
        self.mapy=self.mapx.copy()

        #ang=np.deg2rad(degVec[-1])
        #for i,teta in enumerate(np.array(np.linspace(-ang/2,ang/2,srcX))):
        
        radVec = np.deg2rad(degVec)
        for i,teta in enumerate(radVec):
            for j in range(srcY):
                #b=sy-j-1+10
                b=j*1
                py = b*np.cos(teta)
                px = srcX/2+b*np.sin(teta)
                #mapx[j,i]=px
                #mapy[j,i]=py
                try:
                    self.mapx[int(py),int(px)]=i
                    self.mapy[int(py),int(px)]=j
                except:
                    #import ipdb; ipdb.set_trace()
                    pass


    def warpSonarImage(self, metadata, img):
        sx,sy=img.shape[1],img.shape[0]
        if (sx != self.srcX) or (sy != self.srcY):
            degVec = metadata["beamsDeg"]
            self.createMaps(sx,sy,degVec)
            print('init')

        warped = cv2.remap(img, self.mapx, self.mapy, cv2.INTER_LINEAR)
        
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
