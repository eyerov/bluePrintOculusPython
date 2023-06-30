import cv2
import numpy as np
import math


class warpSonar:
    def __init__(self):
        self.srcX = None
        self.srcY = None

        self.mapx = None
        self.mapy = None


    def jls_extract_def(self):
        
        return 

    def distance(self,x1, y1, x2, y2):
        # Calculating distance
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def angle(self,x1, y1, x2, y2, x3, y3):
        dist1 = self.distance(x1, y1, x2, y2)
        dist2 = self.distance(x3, y3, x2, y2)
        #if (dist1*dist2)==0:
        #    print("calculating angle for ", x1, y1, x2, y2, x3, y3)
        if ((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2)>1:
            return math.acos(1)
        if ((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2)<-1:
            return math.acos(-1)
        return math.acos(((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2))
    def createMaps(self,srcX,srcY,degVec):
        self.srcY = srcY
        self.srcX = srcX
        print("Creating map to warp sonar image")
        deg=max(degVec)
        out_h=1080
        out_w=1920
        self.mapx = np.zeros((out_h, out_w), dtype=np.float32)
        self.mapy = np.zeros((out_h, out_w), dtype=np.float32)
        cx = 888*1920/out_w
        cy = (1080 - 949)*1080/out_h
        rx = 1687*1920/out_w
        ry = (1080 - 575)*1080/out_h
        lx = 89*1920/out_w
        ly = (1080 - 575)*1080/out_h
        r = self.distance(cx, cy, lx, ly)
        pi = 2 * math.asin(1.0)
        src_angl = 130 * pi / 180
        
        for y in range(self.mapx.shape[0]):
            for x in range(self.mapx.shape[1]):
                dist = self.distance(cx, cy, x, y)
                px = 0
                py = 0
                if dist !=0:
                    px = r * (x - cx) / dist + cx
                    py = r * (y - cy) / dist + cy
                else:
                    continue
                
                if px >= lx and px <= rx and dist <= r and y >= cy:
                    angl = self.angle(lx, ly, cx, cy, x, y)
                    angl = angl - deg * pi / 180
                    self.mapy[y, x] = (dist / r) * srcY
                    self.mapx[y, x] = (math.sin(angl) / math.sin(deg * pi / 180) * srcX/2 + srcX/2-0.5)

    def createMaps_old(self, srcX, srcY, degVec):
        print(f"srcX,{srcX},srcY={srcY},degVec={degVec}")

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
            print("sx=",sx,"self.srxX=",self.srcX,"sy=",sy,"self.srcY=",self.srcY)
            self.createMaps(sx,sy,degVec)
            print("sx=",sx,"self.srxX=",self.srcX,"sy=",sy,"self.srcY=",self.srcY)
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

    scales = [1.0, 1.2, 1.5, 2.0, 3.0,3,3,3,3,3]
    
    for scale in scales:

        inImg = cv2.resize(sonImg, None, fx=1, fy=scale)

        warped = ws.warpSonarImage(metadata, inImg)
        warped = cv2.flip(warped, 0)
        print('--->', warped.shape, inImg.shape)

        cv2.imshow('Warped Image', warped)
        cv2.imwrite(f"Warped Image{scale}.jpg", warped)
        cv2.waitKey(0)

    cv2.destroyAllWindows()
