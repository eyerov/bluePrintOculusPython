# bluePrintOculusPython
in process..... 
implementing blue print M1200d Sonar interface, pure python...

this code is used to sample raw Sonar data to gather with its metadata.

No installs is needed (the nic should be in the sonar subnet only).

usage:

python bpSample.py

manual:

    while sonar image is on scope you can do the following actions:
       
        press 'h' to get 512 beams
        press 'n' to get 256 beams
        press 'r' to increase sonar range by 0.5 [m]
        press 'f' to decrease sonar range by -0.5 [m]
        press 'g' to increase gain percentage by 1[%]
        press 'b' to increase gain percentage by 1[%]
        press 'z' to sample 16bit image (it provide 8bit streched image, but at the handler you will have the 16bit)

        TBD...
        
While running the script the first time, it will create "oculus_h.pkl" which hold all the given structs deifed in oculus.h ready to use in python (include the packing string and sizes).

(*) while building that parser I used wireshark to record some transmission between sonar an the PC that halped me understand how to better control the sonar the recorder parser (yen not that perfect but with some crunching you can use it...) and some transimission records are also provided in that repo.

:)
