import socket
import time

from enum import Enum
from typing import Union


PS3MAPI_PORT        = 9671
PS3MAPI_BUF_SIZE    = 1024


class NotConnectedError(Exception):
    pass


class PS3MAPI:
    class Mode(Enum):
        BINARY = 1
        TEXT = 2

    class Command(Enum):
        GET_VERSION = "CORE GETVERSION"
        PROCESS_GETALLPID = "PROCESS GETALLPID"
        PROCESS_GETNAME = "PROCESS GETNAME"
        NOTIFY = "PS3 NOTIFY"
        MEMORY_GET = "MEMORY GET"
        TYPE = "TYPE"
        PASV = "PASV"

    ip = ""                         # type: str
    port = PS3MAPI_PORT             # type: int
    connected = False               # type: bool
    mode = Mode.TEXT
    passive = False
    passive_port = 0

    sock = None                     # type: socket.socket
    data_sock = None                # type: socket.socket
    buffer = bytearray()            # type: bytearray
    leftover_buffer = bytearray()   # type: bytearray

    def __init__(self, ip: str):
        if len(ip.split(":")) > 1:  # support custom ps3mapi port numbers, probably never tested in practice
            self.port = int(ip.split(":")[1])
            ip = ip.split(":")[0]

        self.ip = ip
        self.mode = PS3MAPI.Mode.TEXT

    def _recvuntil(self, byte: int, include=True) -> bytearray:
        """
        Doesn't check if we're connected or not, just naively uses the socket to receive shit

        Also, if you put the byte argument to be anything above 255 or under 0, you're an idiot
        :return:
        """
        self.buffer = self.leftover_buffer.copy()
        self.leftover_buffer = bytearray()

        # Check if what we're looking for might already have been in the leftover buffer
        index = self.buffer.find(byte) + 1
        if index:
            self.leftover_buffer = self.buffer[index:]
            return self.buffer[:index - (0 if include else 1)]

        while True:
            buf = bytearray(PS3MAPI_BUF_SIZE)
            n_bytes = 0
            try:
                n_bytes = self.sock.recv_into(buf, PS3MAPI_BUF_SIZE)
            except socket.timeout:
                print("timeout")

            self.buffer.extend(buf[:n_bytes])

            index = self.buffer.find(byte) + 1
            if index:
                self.leftover_buffer = self.buffer[index:]
                return self.buffer[:index - (0 if include else 1)]

    def _recvline(self, n_lines=1) -> Union[str, list]:
        if n_lines < 2:
            return self._recvuntil(ord('\n'), False).decode('utf-8')
        elif n_lines < 0:
            print("fuck you")
            exit(-1)
        else:
            lines = []

            for _ in range(0,n_lines):
                lines.append(self._recvuntil(ord('\n'), False).decode('utf-8'))

            return lines

    def _set_mode(self, mode: Mode):
        self.mode = mode

        self.command(PS3MAPI.Command.TYPE, "I" if mode == PS3MAPI.Mode.BINARY else "A")

    def connect(self) -> bool:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        self.sock.settimeout(10.0)

        buf = bytearray(PS3MAPI_BUF_SIZE)
        n_bytes = 0
        try:
            n_bytes = self.sock.recv_into(buf, 6)
        except socket.timeout:
            print("timeout")

        if buf[0] != 1:
            return False

        self.connected = True

        return True

    def command(self, command: Command, *args) -> (int, str):
        if not self.connected:
            raise NotConnectedError(f"Could not send command {command}. Not connected to PS3MAPI")

        command_args = ""
        if len(args) > 0:
            command_args = " " + " ".join(args)

        self.sock.send((command.value + command_args + "\r\n").encode('ascii'))

        return self._recvline().replace('\r', '').split(" ", 1)

    def command2(self, command: Command, ignore_result=False, *args) -> (int, str):
        if not self.connected:
            raise NotConnectedError(f"Could not send command {command}. Not connected to PS3MAPI")

        command_args = ""
        if len(args) > 0:
            command_args = " " + " ".join(args)

        self.sock.send((command.value + command_args + "\r\n").encode('ascii'))

        if not ignore_result:
            return self._recvline().replace('\r', '').split(" ", 1)
        else:
            return

    def get_version(self) -> str:
        return self.command(PS3MAPI.Command.GET_VERSION)[1]

    def get_pid_list(self) -> [int]:
        self.sock.send(bytes([0x03]))

        buffer = bytearray(64)
        n_bytes = 0
        while n_bytes < 64:
            try:
                n_bytes += self.sock.recv_into(buffer, 64)
            except socket.timeout:
                print("timeout")

        pids = []
        for i in range(0, 63, 4):
            pids.append(int.from_bytes(buffer[i:i+4], "big"))

        return pids

        result = self.command(PS3MAPI.Command.PROCESS_GETALLPID)[1].split("|")[:-1]
        return list(map(lambda x: int(x), result))

    def process_get_name(self, pid: int) -> str:
        return self.command(PS3MAPI.Command.PROCESS_GETNAME, str(pid))[1]

    def notify(self, msg: str) -> str:
        buffer = [0x02]
        buffer += (len(msg)+1).to_bytes(4, "big")
        buffer += msg.encode('ascii')
        buffer += [0]

        self.sock.send(bytes(buffer))
        return "yo"
        #return self.command(PS3MAPI.Command.NOTIFY, msg)[1]

    def memory_get(self, pid: int, address: int, size: int) -> bytearray:
        buffer = [0x04]
        buffer += pid.to_bytes(4, "big")
        buffer += address.to_bytes(4, "big")
        buffer += size.to_bytes(4, "big")

        self.sock.send(bytes(buffer))

        recv_buffer = bytearray(size)
        n_bytes = 0
        while n_bytes < size:
            try:
                n_bytes += self.sock.recv_into(recv_buffer, size)
            except socket.timeout:
                print("timeout")

        return recv_buffer

        #if self.mode != PS3MAPI.Mode.BINARY:
        #    command_result = self.command(PS3MAPI.Command.TYPE, "I")
        #if self.mode != PS3MAPI.Mode.BINARY and not command_result[0] == "200":
        #    print("O no")
        #    return "WHAT EUHTEWIURTGH"

        if not self.passive:
            result = self.command(PS3MAPI.Command.PASV)[1].split("(", 1)[1].split(")")[0].split(",")
            self.passive = True

            # we don't really use `ip`, we just use the original IP we connected to
            ip = f"{result[0]}.{result[1]}.{result[2]}.{result[3]}"
            self.passive_port = (int(result[4]) << 8) + int(result[5])

            self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.data_sock.connect((self.ip, self.passive_port))
        # self.data_sock.settimeout(0.1)

        self.command(PS3MAPI.Command.MEMORY_GET, str(pid), format(address, 'x'), str(16))

        buffer = bytearray()

        n_bytes = 0

        buf = bytearray(16)
        n_bytes += self.data_sock.recv_into(buf, 16)

        #    if (n_bytes == 0):
        #        break

        buffer.extend(buf[:size])

        # self.data_sock.close()

        self._recvline()

        return buffer


if __name__ == "__main__":
    api = PS3MAPI("10.9.10.15")
    if api.connect():
        print("Connected!")
        api.notify("Holy motherforking shirtballs!")
        api.notify("Can even send two notifications in a row, that's insane!")

        pid_list = api.get_pid_list()

        print(f"pids: {pid_list}")

        while True:
            time.sleep(0.01666667)
            print("\rBolts: " + str(int.from_bytes(api.memory_get(pid_list[2], 0x969CA0, 4), "big")), end="")
    else:
        print("Couldn't connect!")

    #print(f"Version: {api.get_version()}")

    #pid_list = api.get_pid_list()
    #print(f"Pidlist: {api.get_pid_list()}")

    #print("Names for non-zero pids:")
    #for pid in pid_list:
    #    pid = int(pid)
    #    if pid != 0:
    #        print(f"{pid}: {api.process_get_name(pid)}")

    #api.notify("Things seem to be working. Crazy.")

    #while True:
        #api = PS3MAPI("10.9.10.15")
        #api.connect()
    #    time.sleep(0.0166667)
    #    print("\rBolts: " + str(int.from_bytes(api.memory_get(pid_list[2], 0x969CA0, 4), "big")), end="")
