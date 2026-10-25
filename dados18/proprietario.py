"""Read and deliberately alter only the owner of synthetic CI fixtures."""
import ctypes
from ctypes import wintypes as w
k=ctypes.WinDLL('kernel32',use_last_error=True);a=ctypes.WinDLL('advapi32',use_last_error=True)
k.GetCurrentProcess.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE];k.LocalFree.argtypes=[ctypes.c_void_p]
a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
a.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
a.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_wchar_p)]
a.GetNamedSecurityInfoW.argtypes=[w.LPWSTR,ctypes.c_int,w.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)]
a.SetNamedSecurityInfoW.argtypes=[w.LPWSTR,ctypes.c_int,w.DWORD,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
a.ConvertStringSidToSidW.argtypes=[w.LPCWSTR,ctypes.POINTER(ctypes.c_void_p)]
def text(sid):
 p=ctypes.c_wchar_p();assert a.ConvertSidToStringSidW(sid,ctypes.byref(p))
 try:return p.value
 finally:k.LocalFree(p)
def token_sid(kind):
 h=w.HANDLE();assert a.OpenProcessToken(k.GetCurrentProcess(),8,ctypes.byref(h))
 try:
  size=w.DWORD();a.GetTokenInformation(h,kind,None,0,ctypes.byref(size));buf=ctypes.create_string_buffer(size.value)
  assert a.GetTokenInformation(h,kind,buf,size,ctypes.byref(size))
  return text(ctypes.cast(buf,ctypes.POINTER(ctypes.c_void_p))[0])
 finally:k.CloseHandle(h)
def file_owner(path):
 sid=ctypes.c_void_p();sd=ctypes.c_void_p();rc=a.GetNamedSecurityInfoW(str(path),1,1,ctypes.byref(sid),None,None,None,ctypes.byref(sd));assert rc==0,rc
 try:return text(sid)
 finally:k.LocalFree(sd)
def set_owner(path,s):
 sid=ctypes.c_void_p();assert a.ConvertStringSidToSidW(s,ctypes.byref(sid))
 try:
  rc=a.SetNamedSecurityInfoW(str(path),1,1,sid,None,None,None);assert rc==0,rc
 finally:k.LocalFree(sid)
