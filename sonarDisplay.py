import cv2
import numpy as np
import math
from datetime import datetime
import os
import pdb


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
        if (dist1*dist2)==0:
            print("calculating angle for ", x1, y1, x2, y2, x3, y3)
            return 0
        if ((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2)>1:
            return math.acos(1)
        if ((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2)<-1:
            return math.acos(-1)
        return math.acos(((x1 - x2) * (x3 - x2) + (y1 - y2) * (y3 - y2)) / (dist1 * dist2))
    def createMaps(self,srcX,srcY,degVec,final_w=1920,final_h=1080):
        self.srcY = srcY
        self.srcX = srcX
        deg=max(degVec)
        mapfilename=os.path.join(os.path.dirname(__file__),f"oculussonarmap{int(deg)}.pkl")
        print('mapfilename: ', mapfilename)
        st=datetime.now()
        out_h=1080
        out_w=1920
        r_max=math.floor((out_w-2)/math.sin(deg*math.pi/180)/2)
        if srcY>r_max:
            print("since srcY>r_max,",srcY,r_max," need to create a bigger map")
            out_w = 2*math.sin(deg*math.pi/180)*srcY +2
            r_max=math.floor((out_w-2)/math.sin(deg*math.pi/180)/2)
            out_h = r_max+2

            
        cx,cy= (out_w//2,out_h-1)
        rx= cx+int(r_max*math.sin(deg*math.pi/180))
        ry= cy-int(r_max*math.cos(deg*math.pi/180))
        lx= cx-int(r_max*math.sin(deg*math.pi/180))
        ly= ry
        r = r_max
        if os.path.exists(mapfilename):
            with open(mapfilename, 'rb') as fid:
                self.originalmapx,self.originalmapy= pickle.load(fid)
        else:
            print("Creating map to warp sonar image")
            self.originalmapx = np.zeros((out_h, out_w), dtype=np.float32)
            self.originalmapy = np.zeros((out_h, out_w), dtype=np.float32)
            pi = 2 * math.asin(1.0)
            
            for y in range(int(cy-r),self.originalmapx.shape[0]):
                if y<=ly:
                    xmin=cx-math.sqrt(r*r-(cy-y)*(cy-y))
                else:
                    xmin=cx-(cy-y)*math.tan(deg*math.pi/180)
                xmax=cx+cx-xmin

                for x in range(int(xmin),int(xmax)+1):
                    dist = self.distance(cx, cy, x, y)
                    if dist>0:
                        angl = self.angle(lx, ly, cx, cy, x, y)
                        #if x==int(xmin) and y>ly:
                        #    pdb.set_trace()
                        angl = angl - deg * pi / 180
                        self.originalmapx[y, x] = int((math.sin(angl) / math.sin(deg * pi / 180) * srcX/2 + srcX/2-0.5))
                    
                    else:
                        self.originalmapx[y, x] = srcX//2
                        #if abs(self.originalmapx[y, x])<=0.5:
                        #    self.originalmapx[y, x]=0
                    if abs(dist-srcY)<0.5:
                        dist=srcY
                    self.originalmapy[y, x] = int(dist )
                    #if abs(self.originalmapy[y, x]-srcY)<1:
                    #    self.originalmapy[y, x]=srcY-1
            with open(mapfilename, 'ab') as fid:
                pickle.dump((self.originalmapx,self.originalmapy),fid)
        # Here we resize the mapx,mapy to give same size output regardless of input w,h
        r_final=math.floor((final_w-2)/math.sin(deg*math.pi/180)/2)
        #image = cv2.ellipse(image, center_coordinates, axesLength, angle,startAngle, endAngle, color, thickness)
        mask=np.zeros_like(self.originalmapx)
        #import pdb;pdb.set_trace()
        mask   = cv2.ellipse(mask , (cx,cy)           ,(srcY,srcY),  0   ,270-deg    , 270+deg  , 1    ,   -1     )

        print(self.originalmapx.shape,mask.shape)
        #resultx = cv2.bitwise_and(self.originalmapx,mask)
        #resulty = cv2.bitwise_and(self.originalmapy,mask)
        resultx =  np.multiply(self.originalmapx,mask)
        resulty =  np.multiply(self.originalmapy,mask)
        crop_rx= cx+int(srcY*math.sin(deg*math.pi/180))
        crop_lx= cx-int(srcY*math.sin(deg*math.pi/180))
        crop_ymax=cy
        crop_ymin=self.originalmapx.shape[0]-srcY
        crop_w=crop_rx+1-crop_lx
        crop_h=crop_w*final_h//final_w
        assert(crop_ymax-crop_ymin<=crop_h)
        cropped_mask = mask[crop_ymax+1-crop_h:crop_ymax+1,crop_lx:crop_rx+1]
        cropped_resultx = resultx[crop_ymax+1-crop_h:crop_ymax+1,crop_lx:crop_rx+1]
        cropped_resulty = resulty[crop_ymax+1-crop_h:crop_ymax+1,crop_lx:crop_rx+1]
        #cv2.imshow("cropped_mask",cropped_mask);
        #cv2.imshow("cropped_resultx",cropped_resultx);
        #cv2.imshow("cropped_resulty",cropped_resulty);
        self.mapx=cv2.resize(cropped_resultx,(final_w,final_h))
        self.mapy=cv2.resize(cropped_resulty,(final_w,final_h))
        #cv2.waitKey(0)
        
        print(datetime.now()-st)



    def warpSonarImage(self, metadata, img,final_w=1920,final_h=1080,colormap=11):
        sx,sy=img.shape[1],img.shape[0]
        if (sx != self.srcX) or (sy != self.srcY):
            degVec = metadata["beamsDeg"]
            self.createMaps(sx,sy,degVec,final_w=final_w,final_h=final_h)

        #import pdb;pdb.set_trace()
        warped = cv2.remap(img, self.mapx, self.mapy, cv2.INTER_CUBIC)
        color_image=cv2.applyColorMap(warped,colormap)
        return color_image



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
        #inImg=np.ones_like(inImg)*255

        warped = ws.warpSonarImage(metadata, inImg,final_w=1920//2,final_h=1080//2)
        warped = cv2.flip(warped, 0)
        print('--->', warped.shape, inImg.shape)

        cv2.imshow('Warped Image', warped)
        cv2.imwrite(f"Warped Image{scale}.jpg", warped)
        key=cv2.waitKey(0)
        if key==ord("q"):break

    cv2.destroyAllWindows()
