#calls syscall using libc

from ctypes import *

libc = cdll.LoadLibrary("libc.dylib")


def callsys( scn, vi ):
    scallnum = scn #syscall number
    validinput = vi #valid input that syscall takes
    returnVal = 0
    libc.syscall(scallnum, validinput)

    ##example, chmod
    #15 is AUE_CHMOD in BSD/XNU, 0644 is the chmod mask thing
    returnVal = libc.syscall(15, "/Users/yuuko/examples.desktop", 0644)
    return returnVal