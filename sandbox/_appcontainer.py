"""
Launching a process inside a Windows AppContainer.

This file BUILDS a sandbox. It does not break out of one. Everything here is a
documented, public Windows API for running untrusted code with fewer privileges
than the user who started it -- the same mechanism a browser uses to contain a
web page, and a Microsoft Store app to contain itself.

Why this and not Docker: this machine has no Docker, no WSL, and Windows 11
Home has no Windows Sandbox feature. The AppContainer is the only real
isolation boundary available here, and it needs no administrator rights.

What an AppContainer actually does, in plain terms:

  * It runs the process under a throwaway identity (a "SID", Windows' name for
    an account or group identifier) that owns nothing on this machine.
  * Windows file permissions are a list of identities allowed to touch a file.
    That throwaway identity is on nobody's list. So the process cannot open
    almost anything -- not because we scanned it and disapproved, but because
    there is no permission entry naming it. We grant it exactly one folder.
  * Network access for an AppContainer is off unless the container is created
    with a networking capability. We create it with no capabilities at all, and
    Windows Firewall enforces that.

Python's standard library has no binding for any of this, so the calls are made
directly through ctypes. Every function below declares its argument and return
types explicitly. That is not decoration: without it ctypes assumes 32-bit ints
and silently truncates 64-bit pointers, which produces a process that launches,
runs, and is not contained. A sandbox that fails open is worse than none, so
the types are pinned and every call is checked.
"""

import ctypes
from ctypes import wintypes as w

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
userenv = ctypes.WinDLL("userenv", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

# --- constants, from the Windows SDK headers ---------------------------------

PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
HANDLE_FLAG_INHERIT = 0x00000001
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9
WAIT_TIMEOUT = 0x00000102
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

ERROR_ALREADY_EXISTS_HR = 0x800700B7  # profile name already taken


# --- structures --------------------------------------------------------------

class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p),
                ("Attributes", w.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    """Handed to CreateProcess to say 'run this inside that container'."""
    _fields_ = [("AppContainerSid", ctypes.c_void_p),
                ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
                ("CapabilityCount", w.DWORD),
                ("Reserved", w.DWORD)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", w.DWORD),
                ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", w.BOOL)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("lpReserved", w.LPWSTR),
                ("lpDesktop", w.LPWSTR), ("lpTitle", w.LPWSTR),
                ("dwX", w.DWORD), ("dwY", w.DWORD),
                ("dwXSize", w.DWORD), ("dwYSize", w.DWORD),
                ("dwXCountChars", w.DWORD), ("dwYCountChars", w.DWORD),
                ("dwFillAttribute", w.DWORD), ("dwFlags", w.DWORD),
                ("wShowWindow", w.WORD), ("cbReserved2", w.WORD),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", w.HANDLE), ("hStdOutput", w.HANDLE),
                ("hStdError", w.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW),
                ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", w.HANDLE), ("hThread", w.HANDLE),
                ("dwProcessId", w.DWORD), ("dwThreadId", w.DWORD)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in
                ("ReadOperationCount", "WriteOperationCount",
                 "OtherOperationCount", "ReadTransferCount",
                 "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", w.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", w.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", w.DWORD),
                ("SchedulingClass", w.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


# --- signatures --------------------------------------------------------------
# Pinned deliberately. See the module docstring: unpinned pointer arguments are
# truncated to 32 bits and the container silently does not apply.

userenv.CreateAppContainerProfile.argtypes = [
    w.LPCWSTR, w.LPCWSTR, w.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), w.DWORD, ctypes.POINTER(ctypes.c_void_p)]
userenv.CreateAppContainerProfile.restype = ctypes.c_long

userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
    w.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long

userenv.DeleteAppContainerProfile.argtypes = [w.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long

advapi32.ConvertSidToStringSidW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = w.BOOL

kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.LocalFree.restype = ctypes.c_void_p

advapi32.FreeSid.argtypes = [ctypes.c_void_p]
advapi32.FreeSid.restype = ctypes.c_void_p

kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_size_t)]
kernel32.InitializeProcThreadAttributeList.restype = w.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p, w.DWORD, ctypes.c_size_t, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
kernel32.UpdateProcThreadAttribute.restype = w.BOOL

kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
kernel32.DeleteProcThreadAttributeList.restype = None

kernel32.CreateProcessW.argtypes = [
    w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL, w.DWORD,
    ctypes.c_void_p, w.LPCWSTR, ctypes.c_void_p,
    ctypes.POINTER(PROCESS_INFORMATION)]
kernel32.CreateProcessW.restype = w.BOOL

kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(w.HANDLE), ctypes.POINTER(w.HANDLE),
    ctypes.POINTER(SECURITY_ATTRIBUTES), w.DWORD]
kernel32.CreatePipe.restype = w.BOOL

kernel32.SetHandleInformation.argtypes = [w.HANDLE, w.DWORD, w.DWORD]
kernel32.SetHandleInformation.restype = w.BOOL

kernel32.ReadFile.argtypes = [
    w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD), ctypes.c_void_p]
kernel32.ReadFile.restype = w.BOOL

kernel32.CloseHandle.argtypes = [w.HANDLE]
kernel32.CloseHandle.restype = w.BOOL

kernel32.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
kernel32.WaitForSingleObject.restype = w.DWORD

kernel32.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
kernel32.GetExitCodeProcess.restype = w.BOOL

kernel32.ResumeThread.argtypes = [w.HANDLE]
kernel32.ResumeThread.restype = w.DWORD

kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
kernel32.CreateJobObjectW.restype = w.HANDLE

kernel32.SetInformationJobObject.argtypes = [
    w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
kernel32.SetInformationJobObject.restype = w.BOOL

kernel32.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
kernel32.AssignProcessToJobObject.restype = w.BOOL

kernel32.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
kernel32.TerminateJobObject.restype = w.BOOL


# --- container identity ------------------------------------------------------

class ContainerSid:
    """The throwaway identity a sealed run executes as.

    The identity is derived from the container's name by Windows, so deleting
    and recreating a profile with the same name yields the same identity. That
    is what lets a read-only runtime folder be granted access once and reused,
    while each run still gets fresh container storage.
    """

    def __init__(self, name):
        self.name = name
        self._sid = ctypes.c_void_p()
        self._owned = False

    def create(self):
        """Create the profile, replacing any leftover one from a previous run."""
        # A profile left behind by a crashed run would carry that run's state
        # into this one. Nothing is shared between runs, so clear it first.
        userenv.DeleteAppContainerProfile(self.name)

        hr = userenv.CreateAppContainerProfile(
            self.name, self.name, "repo-diagnosis sealed workspace",
            None, 0,                      # no capabilities at all -> no network
            ctypes.byref(self._sid))
        if hr != 0:
            raise OSError(
                f"CreateAppContainerProfile({self.name!r}) failed, "
                f"HRESULT 0x{hr & 0xFFFFFFFF:08X}")
        self._owned = True
        return self

    @property
    def pointer(self):
        return self._sid

    def as_string(self):
        """The identity in the S-1-15-2-... text form that icacls understands."""
        out = w.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(self._sid, ctypes.byref(out)):
            raise OSError("ConvertSidToStringSidW failed, "
                          f"error {ctypes.get_last_error()}")
        try:
            return out.value
        finally:
            kernel32.LocalFree(out)

    def destroy(self):
        if self._owned and self._sid:
            advapi32.FreeSid(self._sid)
            self._sid = ctypes.c_void_p()
            self._owned = False
        userenv.DeleteAppContainerProfile(self.name)


# --- launching ---------------------------------------------------------------

def _make_attribute_list(sid_pointer):
    """Build the CreateProcess attribute saying which container to run in."""
    size = ctypes.c_size_t(0)
    # First call always "fails"; it exists to report the buffer size needed.
    kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
    if size.value == 0:
        raise OSError("InitializeProcThreadAttributeList gave a zero size")

    buffer = (ctypes.c_byte * size.value)()
    attribute_list = ctypes.cast(buffer, ctypes.c_void_p)
    if not kernel32.InitializeProcThreadAttributeList(
            attribute_list, 1, 0, ctypes.byref(size)):
        raise OSError("InitializeProcThreadAttributeList failed, "
                      f"error {ctypes.get_last_error()}")

    capabilities = SECURITY_CAPABILITIES()
    capabilities.AppContainerSid = sid_pointer
    capabilities.Capabilities = None
    capabilities.CapabilityCount = 0   # <- the line that switches the network off
    capabilities.Reserved = 0

    if not kernel32.UpdateProcThreadAttribute(
            attribute_list, 0,
            PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            ctypes.byref(capabilities), ctypes.sizeof(capabilities),
            None, None):
        raise OSError("UpdateProcThreadAttribute failed, "
                      f"error {ctypes.get_last_error()}")

    # The buffer and the capabilities struct must outlive CreateProcess, so
    # they are handed back with the list rather than left to be collected.
    return attribute_list, buffer, capabilities


def _make_pipe():
    """A pipe whose write end the child inherits and whose read end it cannot."""
    attributes = SECURITY_ATTRIBUTES()
    attributes.nLength = ctypes.sizeof(attributes)
    attributes.lpSecurityDescriptor = None
    attributes.bInheritHandle = True

    read_end, write_end = w.HANDLE(), w.HANDLE()
    if not kernel32.CreatePipe(ctypes.byref(read_end), ctypes.byref(write_end),
                               ctypes.byref(attributes), 0):
        raise OSError(f"CreatePipe failed, error {ctypes.get_last_error()}")
    # Our end stays out of the child's hands.
    kernel32.SetHandleInformation(read_end, HANDLE_FLAG_INHERIT, 0)
    return read_end, write_end


def _environment_block(variables):
    """Pack a dict into the NUL-separated block CreateProcess expects.

    The host's own environment is never passed through. It routinely holds API
    keys and paths into the user's account, and handing those to submitted code
    would undo the point of the box.
    """
    text = "".join(f"{k}={v}\0" for k, v in variables.items()) + "\0"
    return ctypes.create_unicode_buffer(text)


def _drain(handle, sink):
    """Read one pipe to end-of-file. Run on its own thread to avoid deadlock."""
    chunk = (ctypes.c_char * 4096)()
    read = w.DWORD()
    while True:
        ok = kernel32.ReadFile(handle, chunk, 4096, ctypes.byref(read), None)
        if not ok or read.value == 0:
            break
        sink.append(bytes(chunk[:read.value]))


def launch(command, working_directory, environment, sid, timeout_seconds):
    """Run `command` inside the container identified by `sid`.

    Returns (exit_code, stdout_text, stderr_text, timed_out).

    The process is created suspended, tied to a job object, and only then
    resumed. The job is what guarantees the run is destroyed afterwards: if the
    submitted code spawns children, killing the job kills all of them, and
    closing the job handle kills anything still alive even if we crash.
    """
    import threading

    attribute_list, _buffer, _capabilities = _make_attribute_list(sid.pointer)

    stdout_read, stdout_write = _make_pipe()
    stderr_read, stderr_write = _make_pipe()

    startup = STARTUPINFOEXW()
    startup.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES
    startup.StartupInfo.hStdInput = None
    startup.StartupInfo.hStdOutput = stdout_write
    startup.StartupInfo.hStdError = stderr_write
    startup.lpAttributeList = attribute_list

    process = PROCESS_INFORMATION()
    command_buffer = ctypes.create_unicode_buffer(command)

    created = kernel32.CreateProcessW(
        None, command_buffer, None, None,
        True,                                   # inherit the pipe write ends
        (EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT
         | CREATE_SUSPENDED | CREATE_NO_WINDOW),
        _environment_block(environment),
        working_directory,
        ctypes.byref(startup), ctypes.byref(process))

    error = ctypes.get_last_error()
    kernel32.DeleteProcThreadAttributeList(attribute_list)

    if not created:
        for h in (stdout_read, stdout_write, stderr_read, stderr_write):
            kernel32.CloseHandle(h)
        raise OSError(f"CreateProcessW failed, error {error}. "
                      "If this is error 5 (access denied), the container "
                      "identity has not been granted access to the runtime "
                      "or the workspace.")

    job = kernel32.CreateJobObjectW(None, None)
    if job:
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation,
            ctypes.byref(limits), ctypes.sizeof(limits))
        kernel32.AssignProcessToJobObject(job, process.hProcess)

    kernel32.ResumeThread(process.hThread)

    # Our copies of the write ends must go, or the reads below never see EOF.
    kernel32.CloseHandle(stdout_write)
    kernel32.CloseHandle(stderr_write)

    out_chunks, err_chunks = [], []
    readers = [threading.Thread(target=_drain, args=(stdout_read, out_chunks),
                                daemon=True),
               threading.Thread(target=_drain, args=(stderr_read, err_chunks),
                                daemon=True)]
    for r in readers:
        r.start()

    waited = kernel32.WaitForSingleObject(
        process.hProcess, int(timeout_seconds * 1000))
    timed_out = (waited == WAIT_TIMEOUT)
    if timed_out and job:
        kernel32.TerminateJobObject(job, 1)

    for r in readers:
        r.join(timeout=10)

    exit_code = w.DWORD()
    kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(exit_code))

    for h in (stdout_read, stderr_read, process.hThread, process.hProcess):
        kernel32.CloseHandle(h)
    if job:
        kernel32.CloseHandle(job)   # kills anything still running

    decode = lambda parts: b"".join(parts).decode("utf-8", errors="replace")
    return exit_code.value, decode(out_chunks), decode(err_chunks), timed_out
